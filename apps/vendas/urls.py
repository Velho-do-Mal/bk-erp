from django.urls import path
from . import views

app_name = 'vendas'

urlpatterns = [
    path('vendas/', views.lista, name='lista'),
    path('vendas/propostas/nova/', views.proposta_nova, name='proposta_nova'),
    path('vendas/propostas/<int:pk>/', views.proposta_detalhe, name='proposta_detalhe'),
    path('vendas/propostas/<int:pk>/exportar-word/', views.exportar_word, name='exportar_word'),
    path('exportar-propostas/', views.exportar_propostas, name='exportar_propostas'),
]
