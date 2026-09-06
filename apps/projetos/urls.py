from django.urls import path
from . import views

app_name = 'projetos'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.novo, name='novo'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/salvar/', views.salvar_dados, name='salvar'),
    path('<int:pk>/encerrar/', views.encerrar, name='encerrar'),
    path('<int:pk>/reabrir/', views.reabrir, name='reabrir'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('<int:pk>/acessos/', views.gerenciar_acessos, name='acessos'),
    path('<int:pk>/controle-docs/', views.controle_docs, name='controle_docs'),
    path('<int:pk>/controle-docs/<int:doc_id>/anexos/', views.api_anexos, name='api_anexos'),
    path('<int:pk>/controle-docs/anexos/<int:anexo_id>/download/', views.download_anexo, name='download_anexo'),
    path('<int:pk>/controle-docs/anexos/<int:anexo_id>/excluir/', views.excluir_anexo, name='excluir_anexo'),
    path('<int:pk>/relatorio-docx/', views.relatorio_docx, name='relatorio_docx'),
]
