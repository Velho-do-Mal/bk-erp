from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.projetos.models import Projeto, ProjetoAcesso


@login_required
def dashboard(request):
    user = request.user
    if user.is_admin_erp:
        total = Projeto.objects.count()
        ativos = Projeto.objects.filter(encerrado=False).count()
        encerrados = Projeto.objects.filter(encerrado=True).count()
        projetos_recentes = Projeto.objects.filter(encerrado=False)[:5]
    else:
        ids = ProjetoAcesso.objects.filter(usuario=user).values_list('projeto_id', flat=True)
        total = len(ids)
        ativos = Projeto.objects.filter(id__in=ids, encerrado=False).count()
        encerrados = Projeto.objects.filter(id__in=ids, encerrado=True).count()
        projetos_recentes = Projeto.objects.filter(id__in=ids, encerrado=False)[:5]

    return render(request, 'core/dashboard.html', {
        'total': total,
        'ativos': ativos,
        'encerrados': encerrados,
        'projetos_recentes': projetos_recentes,
    })


def home(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return redirect('accounts:login')
