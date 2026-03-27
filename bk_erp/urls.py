from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('', include('apps.accounts.urls')),
    path('projetos/', include('apps.projetos.urls')),
    path('', include('apps.cadastros.urls')),
    path('', include('apps.financeiro.urls')),
    path('', include('apps.documentos.urls')),
    path('', include('apps.estoque.urls')),
    path('', include('apps.compras.urls')),
    path('', include('apps.vendas.urls')),
    path('', include('apps.servicos.urls')),
    path('', include('apps.orcamento.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
