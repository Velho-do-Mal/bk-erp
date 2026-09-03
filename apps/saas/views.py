import json
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
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
                'trial_dias': settings.TRIAL_DIAS,
            })

        # CORRIGIDO: quando nenhum plano é selecionado no formulário (ou o
        # campo vem vazio por qualquer motivo), plano_id chega como '' —
        # Plano.objects.filter(id='') estoura ValueError ("expected a
        # number but got ''"), porque o campo id é numérico, e essa
        # exceção não é tratada, então a rota dava Erro 500 sempre que o
        # cadastro era enviado sem plano selecionado. Agora só filtra por
        # id quando plano_id de fato veio preenchido e é numérico.
        plano = None
        if plano_id and plano_id.isdigit():
            plano = Plano.objects.filter(id=plano_id).first()
        if not plano:
            plano = Plano.objects.filter(nome='free').first()

        # Empresa nasce com modulos_contratados no default (todos os módulos —
        # ver apps/saas/models.py) para que o trial seja de acesso completo: é
        # a prática recomendada para maximizar conversão (o cliente avalia o
        # produto inteiro, não uma versão capada). Restringir módulos por
        # contrato é feito depois, manualmente, via Django Admin — para venda
        # negociada/direta, não durante o autocadastro.
        empresa = Empresa.objects.create(
            nome=nome_empresa, cnpj=cnpj, email=email,
            telefone=telefone, plano=plano, ativa=True,
        )
        hoje = datetime.date.today()
        Assinatura.objects.create(
            empresa=empresa, plano=plano,
            status='trial',
            inicio=hoje,
            vencimento=hoje + datetime.timedelta(days=settings.TRIAL_DIAS),
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
        messages.success(request, f'Bem-vindo à {nome_empresa}! Seu trial de {settings.TRIAL_DIAS} dias começou.')
        return redirect('core:dashboard')

    return render(request, 'saas/cadastro.html', {
        'planos': planos, 'bloqueado': bloqueado,
        'trial_dias': settings.TRIAL_DIAS,
    })


def termos(request):
    return render(request, 'saas/termos.html')


def privacidade(request):
    return render(request, 'saas/privacidade.html')
