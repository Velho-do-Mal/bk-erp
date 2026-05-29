from django.urls import path
from . import views
from .busca import busca_global

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('busca/', busca_global, name='busca_global'),
]
