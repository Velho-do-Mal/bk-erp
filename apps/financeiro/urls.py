from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('financeiro/', views.dashboard_financeiro, name='dashboard'),
    path('financeiro/transacoes/', views.transacoes, name='transacoes'),
    path('financeiro/transacoes/<int:pk>/anexo/', views.download_anexo, name='download_anexo'),
    path('financeiro/contas/', views.contas, name='contas'),
    path('financeiro/categorias/', views.categorias, name='categorias'),
]
