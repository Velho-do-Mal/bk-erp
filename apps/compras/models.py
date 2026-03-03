from django.db import models
from apps.cadastros.models import Fornecedor


class PedidoCompra(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('aprovacao', 'Aguardando Aprovação'),
        ('aprovada', 'Aprovada'),
        ('recebida', 'Recebida'),
        ('encerrada', 'Encerrada'),
        ('cancelada', 'Cancelada'),
    ]

    codigo = models.CharField(max_length=100)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='pedidos_compra')
    projeto_nome = models.CharField(max_length=200, blank=True)
    data_pedido = models.DateField()
    data_entrega_prevista = models.DateField(null=True, blank=True)
    data_entrega_real = models.DateField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='aberta')
    observacoes = models.TextField(blank=True)

    # Referência para lançamento financeiro gerado
    transacao_financeiro_ref = models.CharField(max_length=50, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pedido de Compra'
        verbose_name_plural = 'Pedidos de Compra'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.codigo} — {self.fornecedor or 'Sem fornecedor'}"


class ItemPedidoCompra(models.Model):
    pedido = models.ForeignKey(PedidoCompra, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=300)
    codigo_material = models.CharField(max_length=100, blank=True)
    unidade = models.CharField(max_length=20, blank=True)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preco_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.preco_total = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.descricao} x {self.quantidade}"
