from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    path('estoque/', views.lista, name='lista'),
    # CORRIGIDO: "exportar/" (sem prefixo) colidia com apps.documentos, que
    # registra a mesma rota — como documentos é incluído primeiro em
    # bk_erp/urls.py, esta view nunca era alcançada (sempre caía na de
    # documentos, que além disso tinha bug de campo inexistente).
    path('estoque/exportar/', views.exportar_estoque, name='exportar_estoque'),
]
