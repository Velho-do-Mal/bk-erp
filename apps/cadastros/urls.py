from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    path('cadastros/clientes/', views.clientes, name='clientes'),
    path('cadastros/fornecedores/', views.fornecedores, name='fornecedores'),
    path('cadastros/centros-custo/', views.centros_custo, name='centros_custo'),
]
