from django import forms
from django.contrib import admin
from .models import Plano, Empresa, Assinatura
from apps.core.modulos import MODULOS


class EmpresaAdminForm(forms.ModelForm):
    """
    Substitui o textarea JSON cru (padrão do Django Admin para JSONField)
    por uma lista de checkboxes — é aqui que se escolhe quais módulos
    do sistema esta empresa comprou. Vale para todos os usuários dela,
    inclusive administradores (ver User.tem_modulo em apps/accounts/models.py).
    """
    modulos_contratados = forms.MultipleChoiceField(
        choices=MODULOS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Módulos Contratados',
        help_text='Desmarque os módulos que esta empresa NÃO deve acessar.',
    )

    class Meta:
        model = Empresa
        fields = '__all__'


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
    form = EmpresaAdminForm
    list_display = ['nome', 'cnpj', 'email', 'plano', 'ativa', 'criada_em']
    list_filter = ['ativa', 'plano']
    search_fields = ['nome', 'cnpj', 'email']
    inlines = [AssinaturaInline]


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'plano', 'status', 'inicio', 'vencimento', 'valor_pago']
    list_filter = ['status', 'plano']
