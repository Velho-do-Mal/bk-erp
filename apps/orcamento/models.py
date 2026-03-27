from django.db import models
from apps.cadastros.models import Cliente
from apps.servicos.models import ProdutoServico


class MaterialCadastro(models.Model):
    codigo_cliente = models.CharField(max_length=100, blank=True, verbose_name='Código Cliente')
    codigo_bk = models.CharField(max_length=100, blank=True, verbose_name='Código BK')
    descricao = models.CharField(max_length=500, verbose_name='Descrição')
    unidade = models.CharField(max_length=30, default='un', verbose_name='Unidade')
    valor_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name='Valor Unitário'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiais'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class Obra(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Cliente'
    )
    nome = models.CharField(max_length=300, verbose_name='Nome da Obra')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Obra'
        verbose_name_plural = 'Obras'
        ordering = ['-criado_em']

    def __str__(self):
        cliente_nome = self.cliente.nome if self.cliente else 'Sem cliente'
        return f"{self.nome} ({cliente_nome})"


class Orcamento(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='orcamentos', verbose_name='Obra')
    nome = models.CharField(max_length=200, default='Orçamento', verbose_name='Nome')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orçamento'
        verbose_name_plural = 'Orçamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} — {self.obra.nome}"


class ItemMaterial(models.Model):
    orcamento = models.ForeignKey(
        Orcamento, on_delete=models.CASCADE, related_name='itens_material'
    )
    material = models.ForeignKey(
        MaterialCadastro, on_delete=models.PROTECT, verbose_name='Material'
    )
    quantidade = models.DecimalField(
        max_digits=14, decimal_places=3, default=1, verbose_name='Quantidade'
    )
    valor_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name='Valor Unitário'
    )

    class Meta:
        verbose_name = 'Item de Material'
        verbose_name_plural = 'Itens de Material'

    @property
    def valor_total(self):
        return self.quantidade * self.valor_unitario

    def save(self, *args, **kwargs):
        if not self.valor_unitario or self.valor_unitario == 0:
            self.valor_unitario = self.material.valor_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.material.descricao} x {self.quantidade}"


class ItemServico(models.Model):
    orcamento = models.ForeignKey(
        Orcamento, on_delete=models.CASCADE, related_name='itens_servico'
    )
    servico = models.ForeignKey(
        ProdutoServico, on_delete=models.PROTECT, verbose_name='Serviço'
    )
    quantidade = models.DecimalField(
        max_digits=14, decimal_places=3, default=1, verbose_name='Quantidade'
    )
    valor_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name='Valor Unitário'
    )

    class Meta:
        verbose_name = 'Item de Serviço'
        verbose_name_plural = 'Itens de Serviço'

    @property
    def valor_total(self):
        return self.quantidade * self.valor_unitario

    def save(self, *args, **kwargs):
        if not self.valor_unitario or self.valor_unitario == 0:
            self.valor_unitario = self.servico.preco_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.servico.nome} x {self.quantidade}"
