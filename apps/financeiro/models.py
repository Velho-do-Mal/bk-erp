from django.db import models
from apps.cadastros.models import Cliente, Fornecedor, CentrosDeCusto


class Conta(models.Model):
    nome = models.CharField(max_length=200)
    banco = models.CharField(max_length=100, blank=True)
    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ativa = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Conta"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    TIPO_CHOICES = [('entrada', 'Entrada'), ('saida', 'Saída'), ('ambos', 'Ambos')]
    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='ambos')
    pai = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subcategorias')
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoria"
        ordering = ['nome']

    def __str__(self):
        if self.pai:
            return f"{self.pai.nome} → {self.nome}"
        return self.nome


class Transacao(models.Model):
    TIPO_CHOICES = [('entrada', 'Entrada'), ('saida', 'Saída')]
    STATUS_CHOICES = [('pendente', 'Pendente'), ('realizado', 'Realizado')]
    RECORRENCIA_CHOICES = [
        ('', 'Sem recorrência'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]

    descricao = models.CharField(max_length=300)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    data_competencia = models.DateField()
    data_vencimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')

    conta = models.ForeignKey(Conta, on_delete=models.SET_NULL, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)
    centro_custo = models.ForeignKey(CentrosDeCusto, on_delete=models.SET_NULL, null=True, blank=True)

    referencia = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)

    # Recorrência
    recorrencia = models.CharField(max_length=15, choices=RECORRENCIA_CHOICES, blank=True, default='')
    recorrencia_grupo = models.CharField(max_length=50, blank=True)

    # Anexo
    anexo_nome = models.CharField(max_length=300, blank=True)
    anexo_tipo = models.CharField(max_length=100, blank=True)
    anexo_dados = models.BinaryField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transação"
        ordering = ['-data_competencia', '-id']

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"


class Orcamento(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    ano = models.IntegerField()
    mes = models.IntegerField()
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Orçamento"
        unique_together = ('categoria', 'ano', 'mes')
        ordering = ['ano', 'mes']

    def __str__(self):
        return f"{self.categoria} - {self.mes}/{self.ano}"
