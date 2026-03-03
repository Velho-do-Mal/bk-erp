from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    path('documentos/', views.lista, name='lista'),
    path('documentos/download/<int:pk>/', views.download, name='download'),
]
