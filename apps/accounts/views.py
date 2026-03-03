from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', 'core:dashboard'))
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')
