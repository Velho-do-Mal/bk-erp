from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    PERFIL_CHOICES = [
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    ]
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='cliente')
    empresa = models.CharField(max_length=200, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    @property
    def is_admin_erp(self):
        return self.perfil == 'admin' or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_perfil_display()})"
