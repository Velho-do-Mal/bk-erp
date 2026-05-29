from django.contrib import admin
from apps.core.audit import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['criado_em','usuario','empresa','acao','modelo','objeto_id','ip']
    list_filter   = ['acao','modelo','empresa']
    search_fields = ['usuario__username','modelo','detalhe']
    readonly_fields = ['criado_em','usuario','empresa','acao','modelo','objeto_id','detalhe','ip']
    date_hierarchy = 'criado_em'
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
