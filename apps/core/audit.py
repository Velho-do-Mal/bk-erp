"""
BK ERP — Log de Auditoria.
Uso nas views: registrar_auditoria(request, acao, modelo, objeto_id, detalhe='')
"""
from django.db import models


class AuditLog(models.Model):
    ACAO_CHOICES = [
        ('criar',   'Criou'),
        ('editar',  'Editou'),
        ('excluir', 'Excluiu'),
        ('login',   'Login'),
        ('logout',  'Logout'),
        ('exportar','Exportou'),
    ]
    usuario    = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    empresa    = models.ForeignKey(
        'saas.Empresa', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    acao       = models.CharField(max_length=20, choices=ACAO_CHOICES)
    modelo     = models.CharField(max_length=100)
    objeto_id  = models.CharField(max_length=50, blank=True)
    detalhe    = models.TextField(blank=True)
    ip         = models.GenericIPAddressField(null=True, blank=True)
    criado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.usuario} — {self.get_acao_display()} {self.modelo} #{self.objeto_id}"


def registrar(request, acao, modelo, objeto_id='', detalhe=''):
    """Registra uma entrada de auditoria de forma silenciosa (nunca lança exceção)."""
    try:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        usuario = request.user if request.user.is_authenticated else None
        empresa = getattr(request, 'empresa', None)
        AuditLog.objects.create(
            usuario=usuario,
            empresa=empresa,
            acao=acao,
            modelo=modelo,
            objeto_id=str(objeto_id),
            detalhe=detalhe[:500],
            ip=ip or None,
        )
    except Exception:
        pass  # nunca quebra a requisição
