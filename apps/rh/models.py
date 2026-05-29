from django.db import models
from django.db.models import ForeignKey, CASCADE, SET_NULL


class Departamento(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=CASCADE, null=True, blank=True, related_name='+', db_index=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Departamento'

    def __str__(self):
        return self.nome


class Cargo(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=CASCADE, null=True, blank=True, related_name='+', db_index=True)
    nome = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=SET_NULL, null=True, blank=True, related_name='cargos')
    salario_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Cargo'

    def __str__(self):
        return self.nome


class Colaborador(models.Model):
    REGIME_CHOICES = [
        ('clt', 'CLT'),
        ('pj', 'PJ'),
        ('estagio', 'Estágio'),
        ('autonomo', 'Autônomo'),
        ('temporario', 'Temporário'),
    ]
    ESTADO_CIVIL_CHOICES = [
        ('solteiro', 'Solteiro(a)'),
        ('casado', 'Casado(a)'),
        ('divorciado', 'Divorciado(a)'),
        ('viuvo', 'Viúvo(a)'),
        ('uniao_estavel', 'União Estável'),
    ]
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('afastado', 'Afastado'),
        ('ferias', 'Em Férias'),
        ('desligado', 'Desligado'),
    ]
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')]

    empresa = models.ForeignKey('saas.Empresa', on_delete=CASCADE, null=True, blank=True, related_name='+', db_index=True)

    # Dados pessoais
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, blank=True)
    rg = models.CharField(max_length=20, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True)
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=300, blank=True)
    cep = models.CharField(max_length=9, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)

    # Dados profissionais
    matricula = models.CharField(max_length=30, blank=True)
    cargo = models.ForeignKey(Cargo, on_delete=SET_NULL, null=True, blank=True, related_name='colaboradores')
    departamento = models.ForeignKey(Departamento, on_delete=SET_NULL, null=True, blank=True, related_name='colaboradores')
    regime = models.CharField(max_length=20, choices=REGIME_CHOICES, default='clt')
    data_admissao = models.DateField(null=True, blank=True)
    data_demissao = models.DateField(null=True, blank=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')

    # Dados bancários
    banco = models.CharField(max_length=100, blank=True)
    agencia = models.CharField(max_length=20, blank=True)
    conta = models.CharField(max_length=30, blank=True)
    pix = models.CharField(max_length=100, blank=True)

    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Colaborador'

    def __str__(self):
        return self.nome

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        from datetime import date
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def tempo_empresa(self):
        if not self.data_admissao:
            return None
        from datetime import date
        fim = self.data_demissao or date.today()
        anos = (fim - self.data_admissao).days // 365
        return anos


class Ferias(models.Model):
    STATUS_CHOICES = [
        ('agendada', 'Agendada'),
        ('aprovada', 'Aprovada'),
        ('em_gozo', 'Em Gozo'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]
    empresa = models.ForeignKey('saas.Empresa', on_delete=CASCADE, null=True, blank=True, related_name='+', db_index=True)
    colaborador = models.ForeignKey(Colaborador, on_delete=CASCADE, related_name='ferias')
    data_inicio = models.DateField()
    data_fim = models.DateField()
    dias = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendada')
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inicio']
        verbose_name = 'Férias'
        verbose_name_plural = 'Férias'

    def __str__(self):
        return f'Férias {self.colaborador.nome} — {self.data_inicio}'
