from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    path('documentos/', views.lista, name='lista'),
    path('documentos/download/<int:pk>/', views.download, name='download'),
    path('documentos/editar/<int:pk>/', views.editar, name='editar'),
    path('documentos/nova-versao/<int:pk>/', views.nova_versao, name='nova_versao'),
    path('documentos/historico/<int:pk>/', views.historico, name='historico'),
    path('exportar/', views.exportar_documentos, name='exportar_documentos'),
]
