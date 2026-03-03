from django.contrib import admin
from .models import Projeto, ProjetoAcesso


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_inicio', 'gerente', 'encerrado', 'atualizado_em')
    list_filter = ('status', 'encerrado')
    search_fields = ('nome', 'gerente', 'patrocinador')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(ProjetoAcesso)
class ProjetoAcessoAdmin(admin.ModelAdmin):
    list_display = ('projeto', 'usuario', 'criado_em')
    list_filter = ('projeto',)
