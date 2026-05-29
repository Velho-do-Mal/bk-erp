from django.shortcuts import render
from apps.accounts.decorators import admin_required

@admin_required
def dashboard(request):
    return render(request, 'rh/dashboard.html')
