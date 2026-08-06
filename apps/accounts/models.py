from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    PERFIL_CHOICES = [
        ('admin',    'Administrador'),
        ('cliente',  'Cliente'),
        ('superadmin', 'Super Admin'),  # acesso total cross-empresa
    ]
    perfil    = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='cliente')
    empresa   = models.ForeignKey(
        'saas.Empresa',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='usuarios',
        verbose_name='Empresa',
    )
    telefone  = models.CharField(max_length=20, blank=True)
    modulos_permitidos = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Módulos Permitidos',
        help_text='Módulos do sistema que este usuário pode acessar (ignorado para administradores, que sempre têm acesso total).',
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    @property
    def is_admin_erp(self):
        return self.perfil in ('admin', 'superadmin') or self.is_superuser

    @property
    def is_superadmin(self):
        return self.perfil == 'superadmin' or self.is_superuser

    def tem_modulo(self, chave):
        """
        True se o usuário pode acessar o módulo `chave`.

        Ordem de checagem (do mais amplo pro mais restrito):
        1. Superadmin da plataforma (perfil='superadmin' ou is_superuser):
           acesso total, cruza empresas — é quem vende/administra o SaaS.
        2. O módulo precisa estar CONTRATADO pela empresa
           (Empresa.modulos_contratados). Isso vale até para o admin da
           própria empresa: se a empresa não comprou o módulo, ninguém
           dela o acessa — a licença é da empresa, não do usuário.
        3. Dentro do que a empresa contratou: administradores da empresa
           têm acesso a tudo; usuários "cliente" só ao que estiver
           marcado em modulos_permitidos.
        """
        if self.is_superadmin:
            return True
        empresa = self.empresa
        if empresa is not None and not empresa.tem_modulo(chave):
            return False
        if self.is_admin_erp:
            return True
        return chave in (self.modulos_permitidos or [])

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_perfil_display()})"
