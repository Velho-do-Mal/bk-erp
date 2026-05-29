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

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    @property
    def is_admin_erp(self):
        return self.perfil in ('admin', 'superadmin') or self.is_superuser

    @property
    def is_superadmin(self):
        return self.perfil == 'superadmin' or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_perfil_display()})"
