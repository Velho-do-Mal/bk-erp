import csv
import json
from datetime import date, timedelta
from calendar import monthrange
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.financeiro.models import Transacao, Categoria
from apps.projetos.models import Projeto


def _empresa(request):
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    emp = _empresa(request)
    if emp is None:
        return qs
    return qs.filter(empresa=emp)


def _get_periodo(request):
    """Retorna (ano, mes) do filtro GET ou o mês atual."""
    hoje = timezone.now().date()
    try:
        ano = int(request.GET.get('ano', hoje.year))
        mes = int(request.GET.get('mes', hoje.month))
        if not (1 <= mes <= 12):
            mes = hoje.month
    except (ValueError, TypeError):
        ano, mes = hoje.year, hoje.month
    return ano, mes


def _periodo_range(ano, mes):
    _, ultimo = monthrange(ano, mes)
    return date(ano, mes, 1), date(ano, mes, ultimo)


@login_required
def dashboard_relatorios(request):
    hoje = timezone.now().date()
    qs = _qs_empresa(Transacao.objects, request)

    # Resumo dos últimos 12 meses para tabela comparativa
    meses = []
    for i in range(11, -1, -1):
        ref = hoje.replace(day=1) - timedelta(days=i * 28)
        ref = ref.replace(day=1)
        ini, fim = _periodo_range(ref.year, ref.month)
        rec = qs.filter(tipo='entrada', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim).aggregate(Sum('valor'))['valor__sum'] or 0
        desp = qs.filter(tipo='saida', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim).aggregate(Sum('valor'))['valor__sum'] or 0
        meses.append({
            'label': ref.strftime('%b/%y'),
            'receita': float(rec),
            'despesa': float(desp),
            'resultado': float(rec - desp),
        })

    totais = {
        'receita': sum(m['receita'] for m in meses),
        'despesa': sum(m['despesa'] for m in meses),
        'resultado': sum(m['resultado'] for m in meses),
    }

    return render(request, 'relatorios/dashboard.html', {
        'meses': meses,
        'totais': totais,
        'meses_json': json.dumps(meses),
    })


@login_required
def dre(request):
    """DRE — Demonstrativo de Resultado do Exercício por período."""
    ano, mes = _get_periodo(request)
    ini, fim = _periodo_range(ano, mes)
    qs = _qs_empresa(Transacao.objects, request)

    # Receitas por categoria
    receitas = list(
        qs.filter(tipo='entrada', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim)
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    total_receita = sum(r['total'] for r in receitas)

    # Despesas por categoria
    despesas = list(
        qs.filter(tipo='saida', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim)
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    total_despesa = sum(d['total'] for d in despesas)

    resultado = total_receita - total_despesa
    margem = (resultado / total_receita * 100) if total_receita else 0

    # Lista de anos disponíveis (para filtro)
    anos = list(range(timezone.now().year - 3, timezone.now().year + 2))

    return render(request, 'relatorios/dre.html', {
        'receitas': receitas,
        'total_receita': total_receita,
        'despesas': despesas,
        'total_despesa': total_despesa,
        'resultado': resultado,
        'margem': round(margem, 1),
        'ano': ano,
        'mes': mes,
        'ini': ini,
        'fim': fim,
        'anos': anos,
        'meses_nomes': ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],
    })


@login_required
def fluxo_caixa(request):
    """Fluxo de Caixa — movimentações do período selecionado."""
    ano, mes = _get_periodo(request)
    ini, fim = _periodo_range(ano, mes)
    qs = _qs_empresa(Transacao.objects, request)

    transacoes = list(
        qs.filter(data_vencimento__gte=ini, data_vencimento__lte=fim)
        .select_related('categoria')
        .order_by('data_vencimento', 'tipo')
    )

    saldo_acumulado = 0
    saldo_anterior = qs.filter(
        status='realizado', data_pagamento__lt=ini
    ).annotate_saldo = None

    # Calcula saldo anterior ao período
    rec_ant = qs.filter(tipo='entrada', status='realizado', data_pagamento__lt=ini).aggregate(Sum('valor'))['valor__sum'] or 0
    desp_ant = qs.filter(tipo='saida', status='realizado', data_pagamento__lt=ini).aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_anterior = rec_ant - desp_ant

    # Monta fluxo diário
    fluxo = {}
    for t in transacoes:
        dia = t.data_vencimento
        if dia not in fluxo:
            fluxo[dia] = {'entradas': [], 'saidas': [], 'total_entrada': 0, 'total_saida': 0}
        if t.tipo == 'entrada':
            fluxo[dia]['entradas'].append(t)
            fluxo[dia]['total_entrada'] += float(t.valor)
        else:
            fluxo[dia]['saidas'].append(t)
            fluxo[dia]['total_saida'] += float(t.valor)

    # Lista ordenada com saldo acumulado
    fluxo_lista = []
    saldo_acum = saldo_anterior
    for dia in sorted(fluxo.keys()):
        d = fluxo[dia]
        saldo_acum += d['total_entrada'] - d['total_saida']
        fluxo_lista.append({
            'dia': dia,
            'entradas': d['entradas'],
            'saidas': d['saidas'],
            'total_entrada': d['total_entrada'],
            'total_saida': d['total_saida'],
            'saldo': saldo_acum,
        })

    total_entradas = sum(d['total_entrada'] for d in fluxo_lista)
    total_saidas = sum(d['total_saida'] for d in fluxo_lista)
    anos = list(range(timezone.now().year - 3, timezone.now().year + 2))

    return render(request, 'relatorios/fluxo_caixa.html', {
        'fluxo_lista': fluxo_lista,
        'saldo_anterior': saldo_anterior,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_final': saldo_anterior + total_entradas - total_saidas,
        'ano': ano,
        'mes': mes,
        'ini': ini,
        'fim': fim,
        'anos': anos,
        'meses_nomes': ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],
    })


@login_required
def contas_pagar(request):
    """Contas a pagar — pendentes e em atraso."""
    hoje = timezone.now().date()
    qs = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='pendente')

    # Filtros
    status_f = request.GET.get('status', '')  # 'atrasado', 'hoje', 'futuro'
    if status_f == 'atrasado':
        qs = qs.filter(data__lt=hoje)
    elif status_f == 'hoje':
        qs = qs.filter(data_vencimento=hoje)
    elif status_f == 'futuro':
        qs = qs.filter(data__gt=hoje)

    contas = qs.select_related('categoria').order_by('data_vencimento')

    total = qs.aggregate(Sum('valor'))['valor__sum'] or 0
    atrasado = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='pendente', data_vencimento__lt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    vence_hoje = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='pendente', data_vencimento=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    futuro = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='pendente', data_vencimento__gt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0

    return render(request, 'relatorios/contas_pagar.html', {
        'contas': contas,
        'total': total,
        'atrasado': atrasado,
        'vence_hoje': vence_hoje,
        'futuro': futuro,
        'hoje': hoje,
        'status_f': status_f,
    })


@login_required
def contas_receber(request):
    """Contas a receber — pendentes e em atraso."""
    hoje = timezone.now().date()
    qs = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='pendente')

    status_f = request.GET.get('status', '')
    if status_f == 'atrasado':
        qs = qs.filter(data__lt=hoje)
    elif status_f == 'hoje':
        qs = qs.filter(data_vencimento=hoje)
    elif status_f == 'futuro':
        qs = qs.filter(data__gt=hoje)

    contas = qs.select_related('categoria').order_by('data_vencimento')

    total = qs.aggregate(Sum('valor'))['valor__sum'] or 0
    atrasado = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='pendente', data_vencimento__lt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    vence_hoje = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='pendente', data_vencimento=hoje).aggregate(Sum('valor'))['valor__sum'] or 0
    futuro = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='pendente', data_vencimento__gt=hoje).aggregate(Sum('valor'))['valor__sum'] or 0

    return render(request, 'relatorios/contas_receber.html', {
        'contas': contas,
        'total': total,
        'atrasado': atrasado,
        'vence_hoje': vence_hoje,
        'futuro': futuro,
        'hoje': hoje,
        'status_f': status_f,
    })


@login_required
def inadimplencia(request):
    """Relatório de inadimplência — recebimentos atrasados por cliente."""
    hoje = timezone.now().date()
    qs = _qs_empresa(Transacao.objects, request).filter(
        tipo='entrada', status='pendente', data_vencimento__lt=hoje
    ).select_related('categoria').order_by('data_vencimento')

    total = qs.aggregate(Sum('valor'))['valor__sum'] or 0
    count = qs.count()

    # Agrupa por descrição/cliente (simplificado — sem FK de cliente em Transacao)
    por_descricao = list(
        qs.values('descricao')
        .annotate(total=Sum('valor'), qtd=Count('id'))
        .order_by('-total')[:20]
    )

    return render(request, 'relatorios/inadimplencia.html', {
        'contas': qs,
        'total': total,
        'count': count,
        'por_descricao': por_descricao,
        'hoje': hoje,
    })


@login_required
def exportar_dre(request):
    """Exporta DRE do período como CSV."""
    ano, mes = _get_periodo(request)
    ini, fim = _periodo_range(ano, mes)
    qs = _qs_empresa(Transacao.objects, request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="DRE_{ano}_{mes:02d}.csv"'
    response.write('﻿')  # BOM para Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['DEMONSTRATIVO DE RESULTADO DO EXERCÍCIO'])
    writer.writerow([f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}'])
    writer.writerow([])
    writer.writerow(['RECEITAS'])
    writer.writerow(['Categoria', 'Valor (R$)'])

    receitas = qs.filter(tipo='entrada', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim) \
        .values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    total_rec = 0
    for r in receitas:
        writer.writerow([r['categoria__nome'] or 'Sem Categoria', f"{r['total']:.2f}".replace('.', ',')])
        total_rec += r['total']
    writer.writerow(['TOTAL RECEITAS', f"{total_rec:.2f}".replace('.', ',')])
    writer.writerow([])

    writer.writerow(['DESPESAS'])
    writer.writerow(['Categoria', 'Valor (R$)'])
    despesas = qs.filter(tipo='saida', status='realizado', data_pagamento__gte=ini, data_pagamento__lte=fim) \
        .values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    total_desp = 0
    for d in despesas:
        writer.writerow([d['categoria__nome'] or 'Sem Categoria', f"{d['total']:.2f}".replace('.', ',')])
        total_desp += d['total']
    writer.writerow(['TOTAL DESPESAS', f"{total_desp:.2f}".replace('.', ',')])
    writer.writerow([])

    resultado = total_rec - total_desp
    writer.writerow(['RESULTADO LÍQUIDO', f"{resultado:.2f}".replace('.', ',')])

    return response


@login_required
def exportar_fluxo(request):
    """Exporta Fluxo de Caixa do período como CSV."""
    ano, mes = _get_periodo(request)
    ini, fim = _periodo_range(ano, mes)
    qs = _qs_empresa(Transacao.objects, request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="FluxoCaixa_{ano}_{mes:02d}.csv"'
    response.write('﻿')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Descrição', 'Tipo', 'Categoria', 'Status', 'Valor (R$)'])

    transacoes = qs.filter(data_vencimento__gte=ini, data_vencimento__lte=fim).select_related('categoria').order_by('data_vencimento', 'tipo')
    for t in transacoes:
        sinal = '' if t.tipo == 'entrada' else '-'
        writer.writerow([
            t.data_vencimento.strftime('%d/%m/%Y'),
            t.descricao or '',
            'Entrada' if t.tipo == 'entrada' else 'Saída',
            t.categoria.nome if t.categoria else '',
            t.get_status_display(),
            f"{sinal}{t.valor:.2f}".replace('.', ','),
        ])

    return response
