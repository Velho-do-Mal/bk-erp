import csv
import json
from datetime import date, timedelta
from calendar import monthrange
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.core.exportacao import exportar_csv
from apps.financeiro.models import Transacao, Categoria
from apps.projetos.models import Projeto
from apps.vendas.models import Lead, Proposta
from apps.cadastros.models import Cliente
# Reaproveita a mesma regra de visibilidade de projetos usada em
# apps/projetos (admin_erp vê tudo da empresa; demais usuários só os
# projetos em que têm ProjetoAcesso) — pedido do usuário para mover o
# Relatório Executivo de Gestão de Projetos pra este módulo sem duplicar
# essa lógica de permissão.
from apps.projetos.views import get_projetos_usuario


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
    """
    DRE — Demonstrativo de Resultado do Exercício por período.

    CORRIGIDO: um DRE, por definição contábil, é apurado pelo REGIME DE
    COMPETÊNCIA — a receita/despesa é reconhecida no período em que foi
    gerada (data_competencia), independente de já ter sido paga ou não.
    A versão anterior filtrava por data_pagamento + status='realizado',
    ou seja, calculava um resultado de CAIXA e o rotulava como "DRE" —
    isso subestima receitas/despesas já competentes ao período mas ainda
    pendentes de pagamento. O relatório de caixa "de fato" já existe
    separadamente em Fluxo de Caixa (fluxo_caixa, abaixo), que
    corretamente usa data_vencimento/data_pagamento.
    """
    ano, mes = _get_periodo(request)
    ini, fim = _periodo_range(ano, mes)
    qs = _qs_empresa(Transacao.objects, request)

    # Receitas por categoria (regime de competência — todas as receitas
    # cuja competência cai no período, pagas ou não)
    receitas = list(
        qs.filter(tipo='entrada', data_competencia__gte=ini, data_competencia__lte=fim)
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    total_receita = sum(r['total'] for r in receitas)

    # Despesas por categoria (regime de competência)
    despesas = list(
        qs.filter(tipo='saida', data_competencia__gte=ini, data_competencia__lte=fim)
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
    # Calcula saldo anterior ao período
    rec_ant = qs.filter(tipo='entrada', status='realizado', data_pagamento__lt=ini).aggregate(Sum('valor'))['valor__sum'] or 0
    desp_ant = qs.filter(tipo='saida', status='realizado', data_pagamento__lt=ini).aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_anterior = float(rec_ant) - float(desp_ant)

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
        qs = qs.filter(data_vencimento__lt=hoje)
    elif status_f == 'hoje':
        qs = qs.filter(data_vencimento=hoje)
    elif status_f == 'futuro':
        qs = qs.filter(data_vencimento__gt=hoje)

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
        qs = qs.filter(data_vencimento__lt=hoje)
    elif status_f == 'hoje':
        qs = qs.filter(data_vencimento=hoje)
    elif status_f == 'futuro':
        qs = qs.filter(data_vencimento__gt=hoje)

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

    # Agrupa por cliente (Transacao tem FK cliente — usa descrição só quando não há cliente vinculado)
    por_cliente = list(
        qs.values('cliente__id', 'cliente__nome')
        .annotate(total=Sum('valor'), qtd=Count('id'))
        .order_by('-total')[:20]
    )
    for row in por_cliente:
        row['nome_exibicao'] = row['cliente__nome'] or 'Sem cliente vinculado'

    return render(request, 'relatorios/inadimplencia.html', {
        'contas': qs,
        'total': total,
        'count': count,
        'por_cliente': por_cliente,
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
    writer.writerow(['DEMONSTRATIVO DE RESULTADO DO EXERCÍCIO (Regime de Competência)'])
    writer.writerow([f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}'])
    writer.writerow([])
    writer.writerow(['RECEITAS'])
    writer.writerow(['Categoria', 'Valor (R$)'])

    # CORRIGIDO: DRE usa regime de competência (data_competencia), não caixa.
    receitas = qs.filter(tipo='entrada', data_competencia__gte=ini, data_competencia__lte=fim) \
        .values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    total_rec = 0
    for r in receitas:
        writer.writerow([r['categoria__nome'] or 'Sem Categoria', f"{r['total']:.2f}".replace('.', ',')])
        total_rec += r['total']
    writer.writerow(['TOTAL RECEITAS', f"{total_rec:.2f}".replace('.', ',')])
    writer.writerow([])

    writer.writerow(['DESPESAS'])
    writer.writerow(['Categoria', 'Valor (R$)'])
    despesas = qs.filter(tipo='saida', data_competencia__gte=ini, data_competencia__lte=fim) \
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


# ─── Relatório Executivo (movido de Gestão de Projetos — pedido do usuário) ──
#
# Antes vivia em apps/projetos (views.relatorio_executivo,
# templates/projetos/relatorio_executivo.html, rota
# projetos:relatorio-executivo/, botão em templates/projetos/lista.html).
# Passou a viver inteiramente aqui: mesma função, mesmo template (só
# movido de pasta), rota e botão agora em Relatórios. get_projetos_usuario
# é importado de apps.projetos.views para não duplicar a regra de
# visibilidade (admin_erp vê tudo da empresa; demais usuários só os
# projetos em que têm ProjetoAcesso).
@login_required
def relatorio_executivo(request):
    """Gera uma página HTML formatada para impressão do portfólio com dashboards."""
    projetos = get_projetos_usuario(request)
    ativos = projetos.filter(encerrado=False).order_by('-id')
    encerrados = projetos.filter(encerrado=True).order_by('-id')

    # --- Dados Consolidados para Dashboards ---
    total_projetos = ativos.count()
    atrasados = 0
    no_limite = 0
    no_prazo = 0

    total_docs = 0
    docs_status = {
        'concluido': 0,
        'em_analise': 0,
        'atrasado': 0,
        'nao_iniciado': 0,
    }

    total_receitas = 0
    total_despesas = 0

    # Categorias Financeiras (Exemplo baseado nos slides)
    fin_categorias = {
        'Operacional': {'p': 140000, 'r': 108900},
        'Marketing': {'p': 93200, 'r': 78200},
        'Tecnologia': {'p': 98200, 'r': 63300},
        'Administrativo': {'p': 135500, 'r': 145200},
    }

    for p in ativos:
        # Status de Prazo
        if p.data_conclusao:
            if p.data_conclusao < date.today():
                atrasados += 1
            elif p.dias_para_conclusao <= 3:
                no_limite += 1
            else:
                no_prazo += 1
        else:
            no_prazo += 1

        # Dados de Documentos (Controle)
        dados = p.dados or {}
        docs = dados.get('docs', [])
        total_docs += len(docs)

        for d in docs:
            st = d.get('status', 'nao_iniciado')
            if st in ['concluido', 'aprovado']:
                docs_status['concluido'] += 1
            elif st in ['em_analise', 'em_elaboracao', 'em_andamento']:
                docs_status['em_analise'] += 1
            elif st == 'atrasado':
                docs_status['atrasado'] += 1
            else:
                docs_status['nao_iniciado'] += 1

        # Dados Financeiros
        finances = dados.get('finances', [])
        for f in finances:
            val = float(f.get('valor', 0) or 0)
            if f.get('tipo') == 'receita':
                total_receitas += val
            else:
                total_despesas += val

    # Fallback para dados de exemplo se estiver vazio
    if total_docs == 0:
        total_docs = 291
        docs_status = {
            'concluido': 131,
            'em_analise': 87,
            'atrasado': 44,
            'nao_iniciado': 29,
        }

    if total_receitas == 0:
        total_receitas = 182500
        total_despesas = 145200

    saldo_final = total_receitas - total_despesas
    variacao_fluxo = 4.2

    return render(request, 'relatorios/relatorio_executivo.html', {
        'projetos_ativos': ativos,
        'projetos_encerrados': encerrados,
        'today': date.today(),
        'agora': date.today().strftime('%d/%m/%Y'),

        # Dashboards
        'stats_prazo': [atrasados, no_limite, no_prazo],
        'stats_docs': [
            docs_status['concluido'],
            docs_status['em_analise'],
            docs_status['atrasado'],
            docs_status['nao_iniciado'],
        ],
        'total_docs': total_docs,
        'fin_receitas': total_receitas,
        'fin_despesas': total_despesas,
        'fin_saldo': saldo_final,
        'fin_variacao': variacao_fluxo,
        'fin_categorias_json': json.dumps(fin_categorias),

        # Dados para Gráfico de Linhas
        'fin_evolucao_json': json.dumps({
            'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            'planejado': [120000, 135000, 110000, 145000, 130000, 150000],
            'realizado': [105000, 128000, 115000, 142000, 125000, 148000],
        }),
    })


# ─── Relatório de Projetos ────────────────────────────────────────────────

@login_required
def relatorio_projetos(request):
    """Relatório de Projetos — visão consolidada do portfólio (status, prazos, responsáveis)."""
    projetos = get_projetos_usuario(request).order_by('-criado_em')

    status_f = request.GET.get('status', '')
    if status_f:
        projetos = projetos.filter(status=status_f)

    hoje = date.today()
    linhas = []
    atrasados = no_limite = no_prazo = 0
    for p in projetos:
        situacao = None
        if not p.encerrado and p.data_conclusao:
            if p.data_conclusao < hoje:
                situacao = 'atrasado'
                atrasados += 1
            elif p.dias_para_conclusao <= 3:
                situacao = 'no_limite'
                no_limite += 1
            else:
                situacao = 'no_prazo'
                no_prazo += 1
        linhas.append({'projeto': p, 'situacao': situacao})

    total = len(linhas)
    ativos = sum(1 for l in linhas if not l['projeto'].encerrado)
    encerrados = sum(1 for l in linhas if l['projeto'].encerrado)

    return render(request, 'relatorios/projetos.html', {
        'linhas': linhas,
        'total': total,
        'ativos': ativos,
        'encerrados': encerrados,
        'atrasados': atrasados,
        'no_limite': no_limite,
        'no_prazo': no_prazo,
        'status_f': status_f,
        'status_choices': Projeto.STATUS_CHOICES,
    })


@login_required
def exportar_projetos(request):
    """Exporta o Relatório de Projetos como CSV."""
    projetos = get_projetos_usuario(request).order_by('-criado_em')
    hoje = date.today()

    def fmt_data(d):
        return d.strftime('%d/%m/%Y') if d else ''

    def situacao(p):
        if p.encerrado:
            return 'Encerrado'
        if not p.data_conclusao:
            return ''
        if p.data_conclusao < hoje:
            return 'Atrasado'
        if p.dias_para_conclusao <= 3:
            return 'No Limite'
        return 'No Prazo'

    rows = [
        [p.id, p.nome, p.get_status_display(), p.gerente, p.patrocinador,
         fmt_data(p.data_inicio), fmt_data(p.data_conclusao), situacao(p),
         fmt_data(p.criado_em.date() if p.criado_em else None)]
        for p in projetos
    ]
    return exportar_csv('projetos.csv', [
        'ID', 'Projeto', 'Status', 'Gerente', 'Patrocinador',
        'Início', 'Conclusão Prevista', 'Situação do Prazo', 'Cadastrado em',
    ], rows)


# ─── Relatório de Leads ───────────────────────────────────────────────────

@login_required
def relatorio_leads(request):
    """Relatório de Leads — funil comercial consolidado (dados do CRM em Vendas)."""
    leads = _qs_empresa(Lead.objects, request).order_by('-criado_em')

    estagio_f = request.GET.get('estagio', '')
    if estagio_f:
        leads = leads.filter(estagio=estagio_f)
    temperatura_f = request.GET.get('temperatura', '')
    if temperatura_f:
        leads = leads.filter(temperatura=temperatura_f)

    ESTAGIO_LABELS = dict(Lead.ESTAGIO_CHOICES)
    CATEGORIA_LABELS = dict(Lead.CATEGORIA_CHOICES)

    por_estagio = list(
        leads.values('estagio').annotate(qtd=Count('id'), valor=Sum('valor_estimado')).order_by('-valor')
    )
    for row in por_estagio:
        row['label'] = ESTAGIO_LABELS.get(row['estagio'], row['estagio'])

    por_categoria = list(
        leads.exclude(categoria='').values('categoria').annotate(qtd=Count('id'), valor=Sum('valor_estimado')).order_by('-valor')
    )
    for row in por_categoria:
        row['label'] = CATEGORIA_LABELS.get(row['categoria'], row['categoria'])

    total_leads = leads.count()
    total_valor = leads.aggregate(s=Sum('valor_estimado'))['s'] or 0
    pipeline_aberto = leads.filter(estagio__in=['prospeccao', 'proposta']).aggregate(s=Sum('valor_estimado'))['s'] or 0
    ganhos = leads.filter(estagio='fechamento').count()
    perdidos = leads.filter(estagio='perdido').count()
    taxa_conversao = (ganhos / total_leads * 100) if total_leads else 0

    return render(request, 'relatorios/leads.html', {
        'leads': leads,
        'por_estagio': por_estagio,
        'por_categoria': por_categoria,
        'total_leads': total_leads,
        'total_valor': total_valor,
        'pipeline_aberto': pipeline_aberto,
        'ganhos': ganhos,
        'perdidos': perdidos,
        'taxa_conversao': round(taxa_conversao, 1),
        'estagio_f': estagio_f,
        'temperatura_f': temperatura_f,
        'estagio_choices': Lead.ESTAGIO_CHOICES,
        'temperatura_choices': Lead.TEMPERATURA_CHOICES,
    })


@login_required
def exportar_leads(request):
    """Exporta o Relatório de Leads como CSV."""
    leads = _qs_empresa(Lead.objects, request).order_by('-criado_em')
    ESTAGIO_LABELS = dict(Lead.ESTAGIO_CHOICES)
    TEMPERATURA_LABELS = dict(Lead.TEMPERATURA_CHOICES)
    CATEGORIA_LABELS = dict(Lead.CATEGORIA_CHOICES)

    def fmt_data(d):
        return d.strftime('%d/%m/%Y') if d else ''

    rows = [
        [
            l.id, l.nome, l.empresa_nome, l.contato, l.email,
            ESTAGIO_LABELS.get(l.estagio, l.estagio),
            TEMPERATURA_LABELS.get(l.temperatura, l.temperatura),
            CATEGORIA_LABELS.get(l.categoria, l.categoria) if l.categoria else '',
            l.servicos_interesse, float(l.valor_estimado), l.observacoes,
            fmt_data(l.criado_em.date() if l.criado_em else None),
        ]
        for l in leads
    ]
    return exportar_csv('leads.csv', [
        'ID', 'Nome', 'Empresa', 'Contato', 'E-mail', 'Estágio', 'Temperatura',
        'Categoria', 'Serviços de Interesse', 'Valor Estimado (R$)', 'Observações', 'Cadastrado em',
    ], rows)


# ─── Relatório de Propostas ───────────────────────────────────────────────

@login_required
def relatorio_propostas(request):
    """Relatório de Propostas — pipeline de vendas por status, com taxa de conversão."""
    propostas = _qs_empresa(Proposta.objects, request).select_related('cliente', 'lead').order_by('-criado_em')

    status_f = request.GET.get('status', '')
    if status_f:
        propostas = propostas.filter(status=status_f)

    STATUS_LABELS = dict(Proposta.STATUS_CHOICES)
    por_status = list(
        propostas.values('status').annotate(qtd=Count('id'), valor=Sum('valor_total')).order_by('-valor')
    )
    for row in por_status:
        row['label'] = STATUS_LABELS.get(row['status'], row['status'])

    total_propostas = propostas.count()
    total_valor = propostas.aggregate(s=Sum('valor_total'))['s'] or 0
    aprovadas_qs = propostas.filter(status='aprovada')
    aprovadas = aprovadas_qs.count()
    valor_aprovado = aprovadas_qs.aggregate(s=Sum('valor_total'))['s'] or 0
    taxa_conversao = (aprovadas / total_propostas * 100) if total_propostas else 0

    return render(request, 'relatorios/propostas.html', {
        'propostas': propostas,
        'por_status': por_status,
        'total_propostas': total_propostas,
        'total_valor': total_valor,
        'aprovadas': aprovadas,
        'valor_aprovado': valor_aprovado,
        'taxa_conversao': round(taxa_conversao, 1),
        'status_f': status_f,
        'status_choices': Proposta.STATUS_CHOICES,
    })


@login_required
def exportar_propostas(request):
    """Exporta o Relatório de Propostas como CSV."""
    propostas = _qs_empresa(Proposta.objects, request).select_related('cliente', 'lead').order_by('-criado_em')

    def fmt_data(d):
        return d.strftime('%d/%m/%Y') if d else ''

    rows = [
        [
            p.id, p.codigo, p.titulo, p.get_cliente_nome(), p.get_status_display(),
            float(p.valor_total), fmt_data(p.data_emissao), fmt_data(p.data_validade),
            fmt_data(p.criado_em.date() if p.criado_em else None),
        ]
        for p in propostas
    ]
    return exportar_csv('propostas.csv', [
        'ID', 'Código', 'Título', 'Cliente', 'Status', 'Valor Total (R$)',
        'Emissão', 'Validade', 'Cadastrado em',
    ], rows)
