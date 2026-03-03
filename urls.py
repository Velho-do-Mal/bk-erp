from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('', include('apps.accounts.urls')),
    path('projetos/', include('apps.projetos.urls')),
    path('financeiro/', include('apps.financeiro.urls')),
    path('cadastros/', include('apps.cadastros.urls')),
    path('compras/', include('apps.compras.urls')),
    path('vendas/', include('apps.vendas.urls')),
    path('documentos/', include('apps.documentos.urls')),
    path('estoque/', include('apps.estoque.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
