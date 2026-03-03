from django.urls import path
from . import views

app_name = 'vendas'

urlpatterns = [
    path('vendas/', views.lista, name='lista'),
]
