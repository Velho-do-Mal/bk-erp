from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    path('rh/', views.colaboradores, name='dashboard'),
    path('rh/colaboradores/', views.colaboradores, name='colaboradores'),
    path('rh/colaboradores/exportar/', views.exportar_colaboradores, name='exportar_colaboradores'),
    path('rh/departamentos/', views.departamentos, name='departamentos'),
    path('rh/cargos/', views.cargos, name='cargos'),
    path('rh/ferias/', views.ferias, name='ferias'),
]
