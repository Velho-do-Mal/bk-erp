from django.db import models


class ProdutoServico(models.Model):
    TIPO_CHOICES = [
        ('servico', 'Serviço'),
        ('produto', 'Produto'),
        ('ambos', 'Ambos'),
    ]

    codigo = models.CharField(max_length=100, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='servico')
    nome = models.CharField(max_length=300)
    descricao = models.TextField(blank=True)
    unidade = models.CharField(max_length=30, blank=True, default='un')
    preco_unitario = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produto/Serviço'
        verbose_name_plural = 'Produtos/Serviços'
        ordering = ['nome']

    def __str__(self):
        return f"[{self.codigo}] {self.nome}" if self.codigo else self.nome
