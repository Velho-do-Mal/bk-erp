from django.db import models
from django.conf import settings


class Projeto(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('planejamento', 'Planejamento'),
        ('execucao', 'Execução'),
        ('monitoramento', 'Monitoramento'),
        ('encerrado', 'Encerrado'),
        ('suspenso', 'Suspenso'),
    ]

    nome = models.CharField(max_length=300)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='rascunho')
    data_inicio = models.DateField(null=True, blank=True)
    gerente = models.CharField(max_length=200, blank=True)
    patrocinador = models.CharField(max_length=200, blank=True)
    encerrado = models.BooleanField(default=False)

    # JSON completo do projeto (TAP, EAP, Gantt, KPIs, Riscos etc.)
    dados = models.JSONField(default=dict)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"#{self.id} - {self.nome}"

    def get_tap(self):
        return self.dados.get('tap', {})

    def get_eap_tasks(self):
        return self.dados.get('eapTasks', [])

    def get_finances(self):
        return self.dados.get('finances', [])

    def get_kpis(self):
        return self.dados.get('kpis', [])

    def get_risks(self):
        return self.dados.get('risks', [])

    def get_action_plan(self):
        return self.dados.get('actionPlan', [])


class ProjetoAcesso(models.Model):
    """Controla quais clientes têm acesso a quais projetos."""
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='acessos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projetos_acesso')
    pode_ver_tap = models.BooleanField(default=True)
    pode_ver_eap = models.BooleanField(default=True)
    pode_ver_gantt = models.BooleanField(default=True)
    pode_ver_controle = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Acesso ao Projeto'
        verbose_name_plural = 'Acessos aos Projetos'
        unique_together = ('projeto', 'usuario')

    def __str__(self):
        return f"{self.usuario} → {self.projeto}"


class ControleDocConfig(models.Model):
    """Metadados do controle de documentos por projeto."""
    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name='controle_config')
    cliente_nome = models.CharField(max_length=200, blank=True)
    projeto_numero = models.CharField(max_length=100, blank=True)
    projeto_status = models.CharField(max_length=100, blank=True)
    logo_bk_nome = models.CharField(max_length=200, blank=True)
    logo_bk_tipo = models.CharField(max_length=100, blank=True)
    logo_bk_dados = models.BinaryField(null=True, blank=True)
    logo_cliente_nome = models.CharField(max_length=200, blank=True)
    logo_cliente_tipo = models.CharField(max_length=100, blank=True)
    logo_cliente_dados = models.BinaryField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração Controle de Documentos'

    def __str__(self):
        return f"Config Controle — {self.projeto}"


class DocumentoControle(models.Model):
    STATUS_CHOICES = [
        ('nao_iniciado', 'Não iniciado'),
        ('em_andamento', 'Em andamento - BK'),
        ('em_analise', 'Em análise - Cliente'),
        ('em_revisao', 'Em revisão - BK'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='documentos_controle')
    servico_nome = models.CharField(max_length=200, blank=True)
    doc_nome = models.CharField(max_length=300, blank=True)
    doc_numero = models.CharField(max_length=100, blank=True)
    revisao = models.CharField(max_length=20, blank=True, default='R0A')
    responsavel_bk = models.CharField(max_length=200, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nao_iniciado')
    percentual_concluido = models.IntegerField(default=0)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Documento de Controle'
        verbose_name_plural = 'Documentos de Controle'
        ordering = ['id']

    def __str__(self):
        return f"{self.doc_numero} — {self.doc_nome}"

class StatusEventoDocumento(models.Model):
    """Histórico de mudanças de status — base para calcular dias BK x Cliente."""
    documento = models.ForeignKey('DocumentoControle', on_delete=models.CASCADE, related_name='eventos')
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)
    data_evento = models.DateField()
    status = models.CharField(max_length=20)
    responsavel = models.CharField(max_length=10, default='BK')  # BK | CLIENTE
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_evento', 'id']

    def __str__(self):
        return f"{self.documento_id} | {self.status} | {self.data_evento}"
