from django.db import models
from apps.core.storage import media_upload_to
from django.db.models import ForeignKey, CASCADE
from apps.cadastros.models import Cliente, Fornecedor


class Documento(models.Model):
    empresa = models.ForeignKey('saas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name='Empresa', db_index=True)
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
    # Arquivo (FileField)
    arquivo = models.FileField(upload_to=media_upload_to, null=True, blank=True)

    data_validade = models.DateField(null=True, blank=True, verbose_name='Data de Validade', help_text='Deixe em branco se o documento não vence')

    enviado_por = models.CharField(max_length=150, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Versionamento: quando um documento é revisado (ex.: procedimento
    # atualizado), em vez de sobrescrever o arquivo, cria-se um novo
    # registro apontando para o documento original via `documento_original`
    # (sempre a versão 1 do grupo — a v3 também aponta pra v1, não pra v2).
    # `versao` numera sequencialmente e `vigente` marca qual versão do
    # grupo é a válida atualmente; as demais do grupo ficam com
    # vigente=False mas continuam acessíveis (histórico), nunca apagadas.
    documento_original = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='versoes', verbose_name='Documento Original',
        help_text='Preenchido automaticamente quando este registro é uma nova versão de outro documento.'
    )
    versao = models.PositiveIntegerField(default=1, verbose_name='Versão')
    vigente = models.BooleanField(default=True, verbose_name='Vigente', help_text='Indica se esta é a versão válida atual do documento.')

    class Meta:
        verbose_name = "Documento"
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo

    @property
    def raiz_id(self):
        """ID do documento raiz (v1) do grupo de versões deste documento."""
        return self.documento_original_id or self.id
