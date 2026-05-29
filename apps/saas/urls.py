from django.urls import path
from . import views

app_name = 'saas'

urlpatterns = [
    path('precos/',   views.precos,   name='precos'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('termos/', views.termos, name='termos'),
    path('privacidade/', views.privacidade, name='privacidade'),
]
