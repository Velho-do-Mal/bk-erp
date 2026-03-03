from django.db import models
from apps.cadastros.models import Cliente, Fornecedor


class Documento(models.Model):
    TIPO_CHOICES = [
        ('contrato', 'Contratos'),
        ('empresa', 'Doc. Empresa'),
        ('seguro', 'Seguros'),
        ('funcionario', 'Doc. Funcionários'),
        ('cat', 'CATs'),
        ('procedimento', 'Procedimentos'),
        ('medicao', 'Medições'),
        ('nota', 'Notas Fiscais'),
        ('proposta', 'Propostas'),
        ('outro', 'Outros'),
    ]

    titulo = models.CharField(max_length=300)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro')
    tags = models.CharField(max_length=300, blank=True)
    observacoes = models.TextField(blank=True)

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos')
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos')
    projeto_nome = models.CharField(max_length=200, blank=True)  # referência livre ao projeto

    arquivo_nome = models.CharField(max_length=300, blank=True)
    arquivo_tipo = models.CharField(max_length=100, blank=True)
    arquivo_dados = models.BinaryField(null=True, blank=True)

    enviado_por = models.CharField(max_length=150, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo
