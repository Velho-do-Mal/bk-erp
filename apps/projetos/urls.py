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
]
