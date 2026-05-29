import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
from calendar import monthrange
from apps.projetos.models import Projeto, ProjetoAcesso
from apps.financeiro.models import Transacao
from apps.vendas.models import Proposta, Lead
from apps.compras.models import PedidoCompra


def _empresa(request):
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    emp = _empresa(request)
    if emp is None:
        return qs
    return qs.filter(empresa=emp)


@login_required
def dashboard(request):
    user = request.user
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    amanha = hoje + timedelta(days=1)

    # --- PROJETOS ---
    qs_projetos = _qs_empresa(Projeto.objects, request)
    if not user.is_admin_erp:
        ids_acesso = _qs_empresa(ProjetoAcesso.objects, request).filter(usuario=user).values_list('projeto_id', flat=True)
        qs_projetos = qs_projetos.filter(id__in=ids_acesso)

    total_projetos = qs_projetos.count()
    projetos_ativos = qs_projetos.filter(encerrado=False).count()
    projetos_encerrados = qs_projetos.filter(encerrado=True).count()
    projetos_recentes = qs_projetos.filter(encerrado=False).order_by('-data_inicio')[:5]

    # Projetos com prazo vencendo (próximos 7 dias)
    projetos_atrasados = qs_projetos.filter(
        encerrado=False,
        data_fim_prevista__lt=hoje
    ).count()

    # --- FINANCEIRO ---
    qs_trans = _qs_empresa(Transacao.objects, request)

    receita_total = qs_trans.filter(tipo='entrada', status='realizado').aggregate(Sum('valor'))['valor__sum'] or 0
    despesa_total = qs_trans.filter(tipo='saida', status='realizado').aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_atual = receita_total - despesa_total

    receita_mes = qs_trans.filter(tipo='entrada', status='realizado', data__gte=inicio_mes).aggregate(Sum('valor'))['valor__sum'] or 0
    despesa_mes = qs_trans.filter(tipo='saida', status='realizado', data__gte=inicio_mes).aggregate(Sum('valor'))['valor__sum'] or 0

    # Contas a pagar / receber HOJE
    recebimentos_hoje = qs_trans.filter(tipo='entrada', status='pendente', data=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    pagamentos_hoje = qs_trans.filter(tipo='saida', status='pendente', data=hoje).aggregate(Sum('valor'))['valor__sum'] or 0

    # Contas ATRASADAS (vencidas, ainda pendentes)
    recebimentos_atrasados = qs_trans.filter(tipo='entrada', status='pendente', data__lt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    pagamentos_atrasados = qs_trans.filter(tipo='saida', status='pendente', data__lt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    qtd_recebimentos_atrasados = qs_trans.filter(tipo='entrada', status='pendente', data__lt=hoje).count()
    qtd_pagamentos_atrasados = qs_trans.filter(tipo='saida', status='pendente', data__lt=hoje).count()

    # Contas vencendo AMANHÃ
    recebimentos_amanha = qs_trans.filter(tipo='entrada', status='pendente', data=amanha).aggregate(Sum('valor'))['valor__sum'] or 0
    pagamentos_amanha = qs_trans.filter(tipo='saida', status='pendente', data=amanha).aggregate(Sum('valor'))['valor__sum'] or 0

    # --- GRÁFICO: Evolução Mensal (últimos 6 meses) ---
    meses_labels = []
    receitas_mensal = []
    despesas_mensal = []
    for i in range(5, -1, -1):
        mes_ref = hoje.replace(day=1) - timedelta(days=i * 28)
        mes_ref = mes_ref.replace(day=1)
        _, ultimo_dia = monthrange(mes_ref.year, mes_ref.month)
        fim_mes = mes_ref.replace(day=ultimo_dia)
        meses_labels.append(mes_ref.strftime('%b/%y'))
        rec = qs_trans.filter(tipo='entrada', status='realizado', data__gte=mes_ref, data__lte=fim_mes).aggregate(Sum('valor'))['valor__sum'] or 0
        desp = qs_trans.filter(tipo='saida', status='realizado', data__gte=mes_ref, data__lte=fim_mes).aggregate(Sum('valor'))['valor__sum'] or 0
        receitas_mensal.append(float(rec))
        despesas_mensal.append(float(desp))

    chart_evolucao = {
        'labels': meses_labels,
        'receitas': receitas_mensal,
        'despesas': despesas_mensal,
    }

    # --- GRÁFICO: Composição de Despesas por Categoria (Top 5) ---
    despesas_cat = qs_trans.filter(tipo='saida', status='realizado') \
        .values('categoria__nome') \
        .annotate(total=Sum('valor')) \
        .order_by('-total')[:5]
    chart_despesas = {
        'labels': [d['categoria__nome'] or 'Sem Categoria' for d in despesas_cat],
        'values': [float(d['total']) for d in despesas_cat]
    }

    # --- VENDAS ---
    qs_prop = _qs_empresa(Proposta.objects, request)
    qs_leads = _qs_empresa(Lead.objects, request)

    total_propostas = qs_prop.count()
    propostas_aprovadas = qs_prop.filter(status='aprovada').count()
    taxa_conversao = (propostas_aprovadas / total_propostas * 100) if total_propostas > 0 else 0
    valor_propostas = qs_prop.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    ticket_medio = (valor_propostas / total_propostas) if total_propostas > 0 else 0

    # Funil de leads
    leads_estagio = qs_leads.values('estagio').annotate(qtd=Count('id'))
    pipeline_labels = ['Prospecção', 'Qualificação', 'Proposta', 'Negociação']
    pipeline_map = {
        'prospeccao': 'Prospecção', 'qualificacao': 'Qualificação',
        'proposta': 'Proposta', 'negociacao': 'Negociação'
    }
    pipeline_data = [0, 0, 0, 0]
    for l in leads_estagio:
        label = pipeline_map.get(l['estagio'])
        if label in pipeline_labels:
            pipeline_data[pipeline_labels.index(label)] = int(l['qtd'])

    # --- COMPRAS ---
    qs_compras = _qs_empresa(PedidoCompra.objects, request)
    compras_mes = qs_compras.filter(data_pedido__gte=inicio_mes).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    pedidos_pendentes = qs_compras.filter(status__in=['aberta', 'aprovacao']).count()

    # --- ALERTAS DO DIA (lista para exibir na tela) ---
    contas_vencendo_hoje = list(
        qs_trans.filter(status='pendente', data=hoje)
        .select_related('categoria')
        .values('descricao', 'tipo', 'valor', 'data')[:10]
    )
    contas_atrasadas_lista = list(
        qs_trans.filter(status='pendente', data__lt=hoje)
        .select_related('categoria')
        .order_by('data')
        .values('descricao', 'tipo', 'valor', 'data')[:10]
    )

    return render(request, 'core/dashboard.html', {
        # Projetos
        'total': total_projetos,
        'ativos': projetos_ativos,
        'encerrados': projetos_encerrados,
        'projetos_atrasados': projetos_atrasados,
        'projetos_recentes': projetos_recentes,

        # Financeiro KPIs
        'receita_total': receita_total,
        'despesa_total': despesa_total,
        'saldo_atual': saldo_atual,
        'receita_mes': receita_mes,
        'despesa_mes': despesa_mes,

        # Hoje / Amanhã
        'recebimentos_hoje': recebimentos_hoje,
        'pagamentos_hoje': pagamentos_hoje,
        'recebimentos_amanha': recebimentos_amanha,
        'pagamentos_amanha': pagamentos_amanha,

        # Atrasados
        'recebimentos_atrasados': recebimentos_atrasados,
        'pagamentos_atrasados': pagamentos_atrasados,
        'qtd_recebimentos_atrasados': qtd_recebimentos_atrasados,
        'qtd_pagamentos_atrasados': qtd_pagamentos_atrasados,

        # Alertas lista
        'contas_vencendo_hoje': contas_vencendo_hoje,
        'contas_atrasadas_lista': contas_atrasadas_lista,

        # Charts
        'chart_evolucao_json': json.dumps(chart_evolucao),
        'chart_despesas_json': json.dumps(chart_despesas),
        'pipeline_labels_json': json.dumps(pipeline_labels),
        'pipeline_data_json': json.dumps(pipeline_data),

        # Vendas
        'taxa_conversao': round(taxa_conversao, 1),
        'ticket_medio': ticket_medio,
        'total_propostas': total_propostas,
        'propostas_aprovadas': propostas_aprovadas,

        # Compras
        'compras_mes': compras_mes,
        'pedidos_pendentes': pedidos_pendentes,

        # Data
        'hoje': hoje,
    })


def home(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return redirect('accounts:login')
