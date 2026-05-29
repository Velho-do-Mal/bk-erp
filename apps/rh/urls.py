from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    path('rh/', views.dashboard, name='dashboard'),
]
