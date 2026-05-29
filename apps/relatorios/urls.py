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
]
