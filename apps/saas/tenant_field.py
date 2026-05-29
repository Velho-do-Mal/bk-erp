"""
Utilitário: campo FK padrão para empresa (tenant).
Use: empresa = tenant_fk()
"""
from django.db import models
import django.db.models.deletion


def tenant_fk():
    return models.ForeignKey(
        'saas.Empresa',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='+',
        verbose_name='Empresa',
        db_index=True,
    )
