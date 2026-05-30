from django.db import models
from django.db.models import ForeignKey, CASCADE
from apps.cadastros.models import Fornecedor, CentrosDeCusto


class MaterialEstoque(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
    codigo = models.CharField(max_length=100)
    descricao = models.CharField(max_length=300)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)
    centro_custo = models.ForeignKey(
        CentrosDeCusto, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Centro de Custos',
        related_name='materiais_estoque'
    )
    # Legacy: mantido para compatibilidade
    projeto_nome = models.CharField(max_length=200, blank=True)

    qtd_comprada = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    qtd_utilizada = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preco_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    data_compra = models.DateField(null=True, blank=True)
    data_validade = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    pedido_origem = models.ForeignKey(
        'compras.PedidoCompra', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Pedido de Origem',
        related_name='itens_estoque'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Material em Estoque"
        verbose_name_plural = "Estoque de Materiais"
        ordering = ['-data_compra', '-id']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    @property
    def saldo(self):
        return self.qtd_comprada - self.qtd_utilizada
