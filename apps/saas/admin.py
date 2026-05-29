from django.contrib import admin
from .models import Plano, Empresa, Assinatura


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'preco_mensal', 'limite_usuarios', 'limite_projetos', 'limite_propostas', 'ativo']
    list_editable = ['ativo']


class AssinaturaInline(admin.TabularInline):
    model = Assinatura
    extra = 0
    fields = ['plano', 'status', 'inicio', 'vencimento', 'valor_pago']


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'email', 'plano', 'ativa', 'criada_em']
    list_filter = ['ativa', 'plano']
    search_fields = ['nome', 'cnpj', 'email']
    inlines = [AssinaturaInline]


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'plano', 'status', 'inicio', 'vencimento', 'valor_pago']
    list_filter = ['status', 'plano']
