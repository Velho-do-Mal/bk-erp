from django.db import models
from django.db.models import ForeignKey, CASCADE
from apps.cadastros.models import Cliente


class Proposta(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
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

    def save(self, *args, **kwargs):
        # Conversão automática: Lead -> Cliente quando proposta é aprovada
        status_anterior = None
        if self.pk:
            try:
                anterior = self.__class__.objects.get(pk=self.pk)
                status_anterior = anterior.status
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if self.status == 'aprovada' and status_anterior != 'aprovada':
            if self.lead and not self.cliente:
                # CORRIGIDO: faltava empresa=self.empresa no get_or_create.
                # Sem isso, o Cliente criado ficava sem tenant (empresa=None,
                # invisível nas listagens filtradas por empresa) e, pior, o
                # lookup por nome sozinho podia casar com um Cliente de OUTRA
                # empresa com o mesmo nome, atribuindo a proposta a um cliente
                # que não é seu. Também usa a razão social do lead quando
                # disponível (mesma regra de get_cliente_nome).
                cliente, _ = Cliente.objects.get_or_create(
                    nome=self.lead.empresa_nome or self.lead.nome,
                    empresa=self.empresa,
                    defaults={
                        'email': self.lead.email,
                        'telefone': self.lead.contato,
                        'observacoes': self.lead.observacoes,
                        'ativo': True,
                    }
                )
                self.__class__.objects.filter(pk=self.pk).update(cliente=cliente)
                self.cliente = cliente

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
            return self.lead.empresa_nome or self.lead.nome
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
    # CORRIGIDO: existiam DOIS campos chamados "empresa" nesta classe — o
    # ForeignKey de isolamento por tenant (linha abaixo) e um CharField com
    # a razão social do prospect. Em Python, a segunda atribuição sobrescrevia
    # a primeira no namespace da classe, então o ForeignKey NUNCA existiu de
    # fato no model — Lead não tinha isolamento por empresa (tenant), e
    # _qs_empresa(Lead.objects, request) comparava a razão social do prospect
    # com o nome do seu próprio tenant (praticamente nunca batia). Além disso,
    # ao criar um lead novo, a razão social digitada era sobrescrita pelo
    # objeto Empresa do tenant. Renomeado para `empresa_nome` para eliminar
    # a colisão — agora o FK `empresa` funciona corretamente.
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)

    # REVISADO a pedido: o funil agora tem 3 estágios operacionais (o que o
    # usuário efetivamente acompanha no dia a dia) + "Perdido" para marcar
    # oportunidades que não avançam (sem isso não haveria como distinguir um
    # lead esquecido de um lead recusado, e nenhum relatório de conversão
    # funcionaria). Ao chegar em "fechamento", o lead é convertido em Cliente
    # automaticamente — ver save() abaixo.
    ESTAGIO_CHOICES = [
        ('prospeccao', 'Prospecção'),
        ('proposta', 'Proposta Enviada'),
        ('fechamento', 'Fechamento (Ganho)'),
        ('perdido', 'Perdido'),
    ]
    # Temperatura do lead (prioridade de contato) — pedido do usuário.
    TEMPERATURA_CHOICES = [
        ('quente', '🔥 Quente'),
        ('medio', '🟡 Médio'),
        ('frio', '🧊 Frio'),
    ]
    nome = models.CharField(max_length=200)
    empresa_nome = models.CharField('Empresa (razão social do prospect)', max_length=200, blank=True)
    contato = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    estagio = models.CharField(max_length=20, choices=ESTAGIO_CHOICES, default='prospeccao')
    temperatura = models.CharField(max_length=10, choices=TEMPERATURA_CHOICES, default='medio')
    valor_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    # Usado pelo lembrete automático de "leads sem contato há N dias" —
    # qualquer edição no lead reseta a contagem (ver enviar_alertas).
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lead'
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Conversão automática: Lead -> Cliente quando o estágio chega a
        # "Fechamento" (pedido do usuário: "nesse último ele passa
        # automaticamente para cliente"). Só dispara na transição (evita
        # recriar/reprocessar em todo save subsequente do mesmo lead já
        # fechado) e usa empresa=self.empresa para manter o isolamento por
        # tenant (mesmo cuidado tomado na correção do Proposta.save() acima).
        estagio_anterior = None
        if self.pk:
            try:
                estagio_anterior = Lead.objects.get(pk=self.pk).estagio
            except Lead.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        self.cliente_convertido = None
        if self.estagio == 'fechamento' and estagio_anterior != 'fechamento':
            cliente, _ = Cliente.objects.get_or_create(
                nome=self.empresa_nome or self.nome,
                empresa=self.empresa,
                defaults={
                    'email': self.email,
                    'telefone': self.contato,
                    'observacoes': self.observacoes,
                    'ativo': True,
                }
            )
            # Propostas deste lead que ainda não têm cliente vinculado
            # passam a apontar para o cliente recém-criado, preservando o
            # histórico comercial (a referência ao lead original é mantida).
            self.propostas.filter(cliente__isnull=True).update(cliente=cliente)
            self.cliente_convertido = cliente
