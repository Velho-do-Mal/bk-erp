import json
from django_ratelimit.decorators import ratelimit
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import datetime

from .models import Plano, Empresa, Assinatura
from apps.accounts.models import User


def precos(request):
    planos = Plano.objects.filter(ativo=True).order_by('preco_mensal')
    return render(request, 'saas/precos.html', {'planos': planos})


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def cadastro(request):
    bloqueado = request.GET.get('bloqueado')
    planos = Plano.objects.filter(ativo=True).exclude(nome='enterprise').order_by('preco_mensal')

    if request.method == 'POST':
        nome_empresa = request.POST.get('nome_empresa', '').strip()
        cnpj         = request.POST.get('cnpj', '').strip()
        email        = request.POST.get('email', '').strip()
        telefone     = request.POST.get('telefone', '').strip()
        plano_id     = request.POST.get('plano')
        username     = request.POST.get('username', '').strip()
        senha        = request.POST.get('senha', '').strip()
        nome_usuario = request.POST.get('nome_usuario', '').strip()

        erros = []
        if not nome_empresa: erros.append('Nome da empresa é obrigatório.')
        if not email:        erros.append('E-mail é obrigatório.')
        if not username:     erros.append('Nome de usuário é obrigatório.')
        if not senha:        erros.append('Senha é obrigatória.')
        if len(senha) < 6:   erros.append('Senha deve ter pelo menos 6 caracteres.')
        if User.objects.filter(username=username).exists():
            erros.append('Nome de usuário já existe.')

        if erros:
            return render(request, 'saas/cadastro.html', {
                'planos': planos, 'erros': erros,
                'dados': request.POST,
            })

        plano = Plano.objects.filter(id=plano_id).first() or Plano.objects.filter(nome='free').first()

        empresa = Empresa.objects.create(
            nome=nome_empresa, cnpj=cnpj, email=email,
            telefone=telefone, plano=plano, ativa=True,
        )
        hoje = datetime.date.today()
        Assinatura.objects.create(
            empresa=empresa, plano=plano,
            status='trial',
            inicio=hoje,
            vencimento=hoje + datetime.timedelta(days=30),
        )

        user = User.objects.create_user(
            username=username, password=senha,
            email=email, empresa=empresa,
            perfil='admin',
        )
        nomes = nome_usuario.split(' ', 1)
        user.first_name = nomes[0]
        user.last_name  = nomes[1] if len(nomes) > 1 else ''
        user.save()

        login(request, user)
        messages.success(request, f'Bem-vindo à {nome_empresa}! Seu trial de 30 dias começou.')
        return redirect('core:dashboard')

    return render(request, 'saas/cadastro.html', {'planos': planos, 'bloqueado': bloqueado})


def termos(request):
    return render(request, 'saas/termos.html')


def privacidade(request):
    return render(request, 'saas/privacidade.html')
