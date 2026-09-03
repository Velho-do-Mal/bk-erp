from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    path('relatorios/', views.dashboard_relatorios, name='dashboard'),
    path('relatorios/dre/', views.dre, name='dre'),
    path('relatorios/fluxo-caixa/', views.fluxo_caixa, name='fluxo_caixa'),
    path('relatorios/contas-pagar/', views.contas_pagar, name='contas_pagar'),
    path('relatorios/contas-receber/', views.contas_receber, name='contas_receber'),
    path('relatorios/inadimplencia/', views.inadimplencia, name='inadimplencia'),
    path('relatorios/exportar-dre/', views.exportar_dre, name='exportar_dre'),
    path('relatorios/exportar-fluxo/', views.exportar_fluxo, name='exportar_fluxo'),

    # Relatório Executivo — movido do módulo Gestão de Projetos (era
    # projetos:relatorio_executivo, em /projetos/relatorio-executivo/).
    path('relatorios/executivo/', views.relatorio_executivo, name='relatorio_executivo'),

    path('relatorios/projetos/', views.relatorio_projetos, name='relatorio_projetos'),
    path('relatorios/exportar-projetos/', views.exportar_projetos, name='exportar_projetos'),

    path('relatorios/leads/', views.relatorio_leads, name='relatorio_leads'),
    path('relatorios/exportar-leads/', views.exportar_leads, name='exportar_leads'),

    path('relatorios/propostas/', views.relatorio_propostas, name='relatorio_propostas'),
    path('relatorios/exportar-propostas/', views.exportar_propostas, name='exportar_propostas'),
]
