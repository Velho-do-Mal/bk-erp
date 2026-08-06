from django.db import models


def _todos_modulos():
    """
    Default de `Empresa.modulos_contratados`: empresas criadas sem passar
    por um fluxo que defina explicitamente os módulos (ex: script, seed,
    Django Admin sem tocar no campo) recebem acesso total — evita bloquear
    por acidente uma empresa já em produção. Restringir é um ato deliberado
    (Django Admin ou o fluxo de cadastro), nunca um efeito colateral.
    """
    from apps.core.modulos import MODULOS_KEYS
    return list(MODULOS_KEYS)


class Plano(models.Model):
    NOME_CHOICES = [
        ('free',       'Free'),
        ('basic',      'Basic'),
        ('pro',        'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    nome              = models.CharField(max_length=20, choices=NOME_CHOICES, unique=True)
    descricao         = models.TextField(blank=True)
    preco_mensal      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    limite_usuarios   = models.PositiveIntegerField(default=1, help_text='0 = ilimitado')
    limite_projetos   = models.PositiveIntegerField(default=1, help_text='0 = ilimitado')
    limite_propostas  = models.PositiveIntegerField(default=5, help_text='0 = ilimitado')
    ativo             = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        ordering = ['preco_mensal']

    def __str__(self):
        return self.get_nome_display()


class Empresa(models.Model):
    nome          = models.CharField(max_length=200)
    cnpj          = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)
    telefone      = models.CharField(max_length=20, blank=True)
    logo          = models.ImageField(upload_to='logos/', blank=True, null=True)
    plano         = models.ForeignKey(Plano, on_delete=models.PROTECT, null=True, blank=True, related_name='empresas')
    ativa         = models.BooleanField(default=True)
    modulos_contratados = models.JSONField(
        default=_todos_modulos,
        blank=True,
        verbose_name='Módulos Contratados',
        help_text=(
            'Módulos do sistema que esta empresa contratou. Vale para TODOS os '
            'usuários dela, inclusive administradores — se um módulo não está '
            'aqui, ninguém da empresa o acessa. Editável no cadastro da Empresa.'
        ),
    )
    criada_em     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def tem_modulo(self, chave):
        """True se a empresa contratou o módulo `chave`."""
        return chave in (self.modulos_contratados or [])

    @property
    def inadimplente(self):
        """Retorna True se há assinatura vencida e não paga."""
        return self.assinaturas.filter(status='vencida').exists()

    def pode_criar_usuario(self):
        if not self.plano or self.plano.limite_usuarios == 0:
            return True
        return self.usuarios.count() < self.plano.limite_usuarios

    def pode_criar_projeto(self):
        if not self.plano or self.plano.limite_projetos == 0:
            return True
        from apps.projetos.models import Projeto
        return Projeto.objects.filter(empresa=self).count() < self.plano.limite_projetos

    def pode_criar_proposta(self):
        if not self.plano or self.plano.limite_propostas == 0:
            return True
        from apps.vendas.models import Proposta
        return Proposta.objects.filter(empresa=self).count() < self.plano.limite_propostas


class Assinatura(models.Model):
    STATUS_CHOICES = [
        ('ativa',    'Ativa'),
        ('vencida',  'Vencida'),
        ('cancelada','Cancelada'),
        ('trial',    'Trial'),
    ]
    empresa       = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='assinaturas')
    plano         = models.ForeignKey(Plano, on_delete=models.PROTECT)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    inicio        = models.DateField()
    vencimento    = models.DateField()
    valor_pago    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacao    = models.TextField(blank=True)
    criada_em     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        ordering = ['-vencimento']

    def __str__(self):
        return f"{self.empresa} — {self.plano} ({self.get_status_display()})"
