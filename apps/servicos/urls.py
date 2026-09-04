from django.urls import path
from . import views

app_name = 'servicos'

urlpatterns = [
    path('servicos/', views.lista, name='lista'),
    path('servicos/exportar/', views.exportar_servicos, name='exportar_servicos'),
]
