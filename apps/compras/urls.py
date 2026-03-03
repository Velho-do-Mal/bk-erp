from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    path('compras/', views.lista, name='lista'),
]
