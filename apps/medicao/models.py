from django.db import models
from apps.core.storage import media_upload_to
from django.db.models import ForeignKey, CASCADE
from decimal import Decimal

from apps.cadastros.models import Cliente
from apps.servicos.models import ProdutoServico

try:
    from apps.projetos.models import Projeto
except Exception:
    Projeto = None


class BoletimMedicao(models.Model):
    """
    Cabeçalho do Boletim de Medição (BM).
    Agrupa as informações do contrato e do projeto medido.
    """
    empresa = models.ForeignKey(
        'saas.Empresa', on_delete=models.CASCADE,
        null=True, blank=True, related_name='+',
        verbose_name='Empresa', db_index=True
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Cliente"
    )
    projeto = models.ForeignKey(
        "projetos.Projeto", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="boletins_medicao",
        verbose_name="Projeto"
    )
    nome = models.CharField(max_length=300, verbose_name="Nome / Identificação do BM")
    contrato = models.CharField(max_length=200, blank=True, verbose_name="Contrato")
    codigo_obra = models.CharField(max_length=100, blank=True, verbose_name="Código de Obra")

    # Logotipos (FileField)
    logo_bk_nome = models.CharField(max_length=200, blank=True)
    logo_bk_tipo = models.CharField(max_length=100, blank=True)
    logo_bk = models.FileField(upload_to=media_upload_to, null=True, blank=True)
    logo_cliente_nome = models.CharField(max_length=200, blank=True)
    logo_cliente_tipo = models.CharField(max_length=100, blank=True)
    logo_cliente = models.FileField(upload_to=media_upload_to, null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Boletim de Medição"
        verbose_name_plural = "Boletins de Medição"
        ordering = ["-criado_em"]

    def __str__(self):
        cliente_nome = self.cliente.nome if self.cliente else "Sem cliente"
        return f"{self.nome} ({cliente_nome})"

    @property
    def proximo_numero_bm(self):
        """Retorna o próximo número de BM (último + 1)."""
        ultimo = self.periodos.order_by("-numero").first()
        return (ultimo.numero + 1) if ultimo else 1

    @property
    def total_contrato(self):
        return sum(item.preco_total for item in self.itens.all())


class ItemContrato(models.Model):
    """
    Linha do contrato — define cada item/atividade e seu valor total contratado.
    Equivale à grade da Aba 'Cadastro dos Itens'.
    """
    boletim = models.ForeignKey(
        BoletimMedicao, on_delete=models.CASCADE,
        related_name="itens", verbose_name="Boletim"
    )
    servico = models.ForeignKey(
        ProdutoServico, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Serviço/Atividade"
    )
    codigo = models.CharField(max_length=100, blank=True, verbose_name="Código")
    descricao = models.CharField(max_length=500, verbose_name="Descrição")
    quantidade_total = models.DecimalField(
        max_digits=14, decimal_places=3, default=1,
        verbose_name="Qtde Total"
    )
    unidade = models.CharField(max_length=30, default="un", verbose_name="Unidade")
    preco_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name="Preço Unitário"
    )
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Item do Contrato"
        verbose_name_plural = "Itens do Contrato"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"[{self.codigo}] {self.descricao}" if self.codigo else self.descricao

    @property
    def preco_total(self):
        qty = self.quantidade_total or Decimal("0")
        pu = self.preco_unitario or Decimal("0")
        return qty * pu

    def save(self, *args, **kwargs):
        # Preenche código e dados automaticamente a partir do serviço
        if self.servico and not self.codigo:
            self.codigo = self.servico.codigo or ""
        if self.servico and not self.descricao:
            self.descricao = self.servico.nome
        if self.servico and (not self.preco_unitario or self.preco_unitario == 0):
            self.preco_unitario = self.servico.preco_unitario
        if self.servico and not self.unidade:
            self.unidade = self.servico.unidade or "un"
        super().save(*args, **kwargs)


class PeriodoMedicao(models.Model):
    """
    Um período de medição (BM-1, BM-2, …).
    Cada período tem um número sequencial e intervalo de datas.
    """
    boletim = models.ForeignKey(
        BoletimMedicao, on_delete=models.CASCADE,
        related_name="periodos", verbose_name="Boletim"
    )
    numero = models.PositiveIntegerField(verbose_name="Número BM")
    data_inicio = models.DateField(verbose_name="Data Início")
    data_fim = models.DateField(verbose_name="Data Fim")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Período de Medição"
        verbose_name_plural = "Períodos de Medição"
        ordering = ["numero"]
        unique_together = ("boletim", "numero")

    def __str__(self):
        return f"BM-{self.numero} — {self.boletim.nome}"

    @property
    def label(self):
        return f"BM-{self.numero}"

    @property
    def valor_total_periodo(self):
        return sum(m.valor_medido for m in self.medicoes.all())


class MedicaoItem(models.Model):
    """
    Quantidade medida de um ItemContrato em um PeriodoMedicao específico.
    """
    periodo = models.ForeignKey(
        PeriodoMedicao, on_delete=models.CASCADE,
        related_name="medicoes", verbose_name="Período"
    )
    item = models.ForeignKey(
        ItemContrato, on_delete=models.CASCADE,
        related_name="medicoes", verbose_name="Item"
    )
    quantidade_medida = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        verbose_name="Quantidade Medida"
    )

    class Meta:
        verbose_name = "Medição do Item"
        verbose_name_plural = "Medições dos Itens"
        unique_together = ("periodo", "item")

    def __str__(self):
        return f"{self.item} | BM-{self.periodo.numero} = {self.quantidade_medida}"

    @property
    def valor_medido(self):
        qtd = self.quantidade_medida or Decimal("0")
        pu = self.item.preco_unitario or Decimal("0")
        return qtd * pu
