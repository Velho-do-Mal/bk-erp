from django.db import models
from django.db.models import ForeignKey, CASCADE


class Cliente(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Fornecedor(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fornecedor"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class CentrosDeCusto(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
    nome = models.CharField(max_length=200)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"
        ordering = ['nome']

    def __str__(self):
        return self.nome
