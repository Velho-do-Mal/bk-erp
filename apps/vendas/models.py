from django.db import models
from apps.cadastros.models import Cliente


class Proposta(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('enviada', 'Enviada'),
        ('negociacao', 'Em Negociacao'),
        ('aprovada', 'Aprovada'),
        ('perdida', 'Perdida'),
        ('cancelada', 'Cancelada'),
    ]

    codigo = models.CharField(max_length=100)
    titulo = models.CharField(max_length=300)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='propostas'
    )
    lead = models.ForeignKey(
        'Lead', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='propostas'
    )
    projeto_nome = models.CharField(max_length=200, blank=True)
    data_emissao = models.DateField()
    data_validade = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='rascunho')
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    condicoes_pagamento = models.CharField(max_length=200, blank=True)
    prazo_execucao = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)
    notas_tecnicas = models.TextField(blank=True)
    dados_orcamento = models.JSONField(default=dict, blank=True)
    transacao_financeiro_ref = models.CharField(max_length=50, blank=True)
    projeto_ref_id = models.IntegerField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proposta'
        verbose_name_plural = 'Propostas'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

    def get_cliente_nome(self):
        if self.cliente:
            return self.cliente.nome
        if self.lead:
            return self.lead.empresa or self.lead.nome
        return ''

    def get_cliente_tipo(self):
        if self.cliente_id:
            return 'cliente'
        if self.lead_id:
            return 'lead'
        return ''

    def get_cliente_ref(self):
        if self.cliente_id:
            return {'tipo': 'cliente', 'id': self.cliente_id}
        if self.lead_id:
            return {'tipo': 'lead', 'id': self.lead_id}
        return {'tipo': '', 'id': None}


class ItemProposta(models.Model):
    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=300)
    unidade = models.CharField(max_length=20, blank=True)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preco_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ordem = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.preco_total = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['ordem', 'id']

    def __str__(self):
        return self.descricao


class Lead(models.Model):
    ESTAGIO_CHOICES = [
        ('prospeccao', 'Prospeccao'),
        ('qualificacao', 'Qualificacao'),
        ('proposta', 'Proposta Enviada'),
        ('negociacao', 'Negociacao'),
        ('fechado_ganho', 'Fechado Ganho'),
        ('fechado_perdido', 'Fechado Perdido'),
    ]
    nome = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200, blank=True)
    contato = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    estagio = models.CharField(max_length=20, choices=ESTAGIO_CHOICES, default='prospeccao')
    valor_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lead'
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome
