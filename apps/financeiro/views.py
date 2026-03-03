import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from .models import Conta, Categoria, Transacao, Orcamento
from apps.cadastros.models import Cliente, Fornecedor, CentrosDeCusto


def _to_dec(v):
    try:
        return Decimal(str(v or 0))
    except Exception:
        return Decimal('0')


def _to_date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


RECORRENCIA_DELTAS = {
    'semanal': lambda d: d + timedelta(weeks=1),
    'quinzenal': lambda d: d + timedelta(days=15),
    'mensal': lambda d: d + relativedelta(months=1),
    'bimestral': lambda d: d + relativedelta(months=2),
    'trimestral': lambda d: d + relativedelta(months=3),
    'semestral': lambda d: d + relativedelta(months=6),
    'anual': lambda d: d + relativedelta(years=1),
}


@login_required
def download_anexo(request, pk):
    t = get_object_or_404(Transacao, pk=pk)
    if not t.anexo_dados:
        from django.http import Http404
        raise Http404
    resp = HttpResponse(bytes(t.anexo_dados), content_type=t.anexo_tipo or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{t.anexo_nome}"'
    return resp


@login_required
def dashboard_financeiro(request):
    from django.db.models.functions import TruncMonth
    from apps.cadastros.models import CentrosDeCusto

    hoje = date.today()

    # ── Filtros de período ──────────────────────────────────
    ini_str = request.GET.get('data_ini', '')
    fim_str = request.GET.get('data_fim', '')
    modo    = request.GET.get('modo', 'todos')   # realizado | previsto | todos

    try:
        d_ini = date.fromisoformat(ini_str) if ini_str else date(hoje.year, 1, 1)
    except ValueError:
        d_ini = date(hoje.year, 1, 1)
    try:
        d_fim = date.fromisoformat(fim_str) if fim_str else hoje
    except ValueError:
        d_fim = hoje

    def _qs_base():
        qs = Transacao.objects.filter(data_competencia__gte=d_ini, data_competencia__lte=d_fim)
        if modo == 'realizado':
            qs = qs.filter(status='realizado')
        elif modo == 'previsto':
            qs = qs.filter(status='pendente')
        return qs

    # ── KPIs globais (sem filtro de período p/ saldo total) ─
    total_entrada = Transacao.objects.filter(tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    total_saida   = Transacao.objects.filter(tipo='saida',   status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    saldo = total_entrada - total_saida
    pendentes_receber = Transacao.objects.filter(tipo='entrada', status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    pendentes_pagar   = Transacao.objects.filter(tipo='saida',   status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    # KPIs do período filtrado
    ent_periodo  = _qs_base().filter(tipo='entrada').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    said_periodo = _qs_base().filter(tipo='saida').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    ultimas = list(Transacao.objects.select_related('categoria', 'conta').order_by('-criado_em')[:10].values(
        'id', 'descricao', 'tipo', 'valor', 'status', 'data_competencia', 'categoria__nome', 'conta__nome'
    ))

    # ── Fluxo de Caixa mensal ──────────────────────────────
    meses_raw = (
        _qs_base()
        .annotate(mes=TruncMonth('data_competencia'))
        .values('mes', 'tipo')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )
    meses_data = {}
    for m in meses_raw:
        key = m['mes'].strftime('%Y-%m') if m['mes'] else ''
        if key not in meses_data:
            meses_data[key] = {'entrada': 0, 'saida': 0}
        meses_data[key][m['tipo']] = float(m['total'] or 0)

    # Acumulado
    keys_sorted = sorted(meses_data.keys())
    acum = 0.0
    for k in keys_sorted:
        acum += meses_data[k].get('entrada', 0) - meses_data[k].get('saida', 0)
        meses_data[k]['acumulado'] = round(acum, 2)

    # ── Pizza: categorias de SAÍDA ─────────────────────────
    cat_saida = (
        _qs_base()
        .filter(tipo='saida')
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    cat_saida_data = [
        {'nome': r['categoria__nome'] or 'Sem categoria', 'total': float(r['total'] or 0)}
        for r in cat_saida
    ]

    # ── Centros de Custo ───────────────────────────────────
    cc_entradas = (
        _qs_base()
        .filter(tipo='entrada')
        .values('centro_custo__nome')
        .annotate(total=Sum('valor'))
    )
    cc_saidas = (
        _qs_base()
        .filter(tipo='saida')
        .values('centro_custo__nome')
        .annotate(total=Sum('valor'))
    )
    cc_map = {}
    for r in cc_entradas:
        k = r['centro_custo__nome'] or 'Sem CC'
        cc_map.setdefault(k, {'entrada': 0, 'saida': 0})['entrada'] = float(r['total'] or 0)
    for r in cc_saidas:
        k = r['centro_custo__nome'] or 'Sem CC'
        cc_map.setdefault(k, {'entrada': 0, 'saida': 0})['saida'] = float(r['total'] or 0)

    cc_data = []
    for nome, vals in cc_map.items():
        saldo_cc = vals['entrada'] - vals['saida']
        pct = round(saldo_cc / vals['entrada'] * 100, 1) if vals['entrada'] > 0 else 0
        cc_data.append({'nome': nome, 'entrada': vals['entrada'], 'saida': vals['saida'],
                        'saldo': round(saldo_cc, 2), 'pct': pct})
    cc_data.sort(key=lambda x: x['saldo'], reverse=True)

    ctx = {
        'total_entrada':    total_entrada,
        'total_saida':      total_saida,
        'saldo':            saldo,
        'pendentes_receber': pendentes_receber,
        'pendentes_pagar':   pendentes_pagar,
        'ent_periodo':      ent_periodo,
        'said_periodo':     said_periodo,
        'saldo_periodo':    ent_periodo - said_periodo,
        'ultimas_json':     json.dumps(ultimas, default=str),
        'meses_json':       json.dumps(meses_data),
        'cat_saida_json':   json.dumps(cat_saida_data),
        'cc_json':          json.dumps(cc_data),
        'data_ini':         d_ini.isoformat(),
        'data_fim':         d_fim.isoformat(),
        'modo':             modo,
    }
    return render(request, 'financeiro/dashboard.html', ctx)


@login_required
def transacoes(request):
    if request.method == 'POST' and request.FILES.get('anexo'):
        # Upload com form multipart (criação com anexo)
        f = request.FILES['anexo']
        rid = request.POST.get('id') or None
        obj = Transacao.objects.get(id=int(rid)) if rid else Transacao()
        obj.descricao = request.POST.get('descricao', '').strip()
        obj.tipo = request.POST.get('tipo', 'saida')
        obj.valor = _to_dec(request.POST.get('valor', 0))
        obj.data_competencia = _to_date(request.POST.get('data_competencia')) or date.today()
        obj.data_vencimento = _to_date(request.POST.get('data_vencimento'))
        obj.data_pagamento = _to_date(request.POST.get('data_pagamento'))
        obj.status = request.POST.get('status', 'pendente')
        obj.recorrencia = request.POST.get('recorrencia', '')
        obj.referencia = request.POST.get('referencia', '').strip()
        obj.observacoes = request.POST.get('observacoes', '').strip()
        cid = request.POST.get('conta_id')
        obj.conta_id = int(cid) if cid else None
        catid = request.POST.get('categoria_id')
        obj.categoria_id = int(catid) if catid else None
        clid = request.POST.get('cliente_id')
        obj.cliente_id = int(clid) if clid else None
        fid = request.POST.get('fornecedor_id')
        obj.fornecedor_id = int(fid) if fid else None
        ccid = request.POST.get('centro_custo_id')
        obj.centro_custo_id = int(ccid) if ccid else None
        obj.anexo_nome = f.name
        obj.anexo_tipo = f.content_type or 'application/octet-stream'
        obj.anexo_dados = f.read()
        obj.save()
        _gerar_recorrencia(obj)
        return JsonResponse({'ok': True, 'id': obj.id})

    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            rid = data.get('id')
            obj = Transacao.objects.get(id=rid) if rid else Transacao()
            obj.descricao = data.get('descricao', '').strip()
            obj.tipo = data.get('tipo', 'saida')
            obj.valor = _to_dec(data.get('valor', 0))
            obj.data_competencia = _to_date(data.get('data_competencia')) or date.today()
            obj.data_vencimento = _to_date(data.get('data_vencimento'))
            obj.data_pagamento = _to_date(data.get('data_pagamento'))
            obj.status = data.get('status', 'pendente')
            obj.recorrencia = data.get('recorrencia', '')
            obj.referencia = data.get('referencia', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            cid = data.get('conta_id')
            obj.conta_id = int(cid) if cid else None
            catid = data.get('categoria_id')
            obj.categoria_id = int(catid) if catid else None
            clid = data.get('cliente_id')
            obj.cliente_id = int(clid) if clid else None
            fid = data.get('fornecedor_id')
            obj.fornecedor_id = int(fid) if fid else None
            ccid = data.get('centro_custo_id')
            obj.centro_custo_id = int(ccid) if ccid else None
            is_new = not obj.pk
            obj.save()
            if is_new:
                _gerar_recorrencia(obj)
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            Transacao.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'toggle_status':
            obj = get_object_or_404(Transacao, id=data.get('id'))
            obj.status = 'realizado' if obj.status == 'pendente' else 'pendente'
            if obj.status == 'realizado' and not obj.data_pagamento:
                obj.data_pagamento = date.today()
            obj.save()
            return JsonResponse({'ok': True, 'status': obj.status})

    # Filtros
    tipo_f   = request.GET.get('tipo', '')
    status_f = request.GET.get('status', '')
    mes_f    = request.GET.get('mes', '')
    ini_f    = request.GET.get('data_ini', '')
    fim_f    = request.GET.get('data_fim', '')

    qs = Transacao.objects.select_related('conta', 'categoria', 'cliente', 'fornecedor', 'centro_custo')
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if status_f:
        qs = qs.filter(status=status_f)
    # Período: data_ini/data_fim têm prioridade sobre mes
    if ini_f or fim_f:
        try:
            if ini_f:
                qs = qs.filter(data_competencia__gte=date.fromisoformat(ini_f))
            if fim_f:
                qs = qs.filter(data_competencia__lte=date.fromisoformat(fim_f))
        except ValueError:
            pass
    elif mes_f:
        try:
            ano, mes = mes_f.split('-')
            qs = qs.filter(data_competencia__year=ano, data_competencia__month=mes)
        except Exception:
            pass

    transacoes_list = list(qs.values(
        'id', 'descricao', 'tipo', 'valor', 'status',
        'data_competencia', 'data_vencimento', 'data_pagamento',
        'conta__nome', 'categoria__nome', 'cliente__nome',
        'fornecedor__nome', 'centro_custo__nome', 'referencia',
        'conta_id', 'categoria_id', 'cliente_id', 'fornecedor_id', 'centro_custo_id',
        'observacoes', 'recorrencia', 'recorrencia_grupo',
        'anexo_nome', 'anexo_tipo',
    ))

    contas = list(Conta.objects.filter(ativa=True).values('id', 'nome'))
    categorias = list(Categoria.objects.values('id', 'nome', 'tipo'))
    clientes = list(Cliente.objects.filter(ativo=True).values('id', 'nome'))
    fornecedores_list = list(Fornecedor.objects.filter(ativo=True).values('id', 'nome'))
    centros = list(CentrosDeCusto.objects.filter(ativo=True).values('id', 'nome'))

    ctx = {
        'transacoes_json':  json.dumps(transacoes_list, default=str),
        'contas_json':       json.dumps(contas),
        'categorias_json':   json.dumps(categorias),
        'clientes_json':     json.dumps(clientes),
        'fornecedores_json': json.dumps(fornecedores_list),
        'centros_json':      json.dumps(centros),
        'tipo_f':   tipo_f,
        'status_f': status_f,
        'mes_f':    mes_f,
        'ini_f':    ini_f,
        'fim_f':    fim_f,
    }
    return render(request, 'financeiro/transacoes.html', ctx)




def _gerar_recorrencia(origem: Transacao):
    """Gera cópias futuras para transações recorrentes (12 repetições)."""
    rec = origem.recorrencia
    if not rec or rec not in RECORRENCIA_DELTAS:
        return
    delta_fn = RECORRENCIA_DELTAS[rec]
    grupo = str(uuid.uuid4())[:8]
    origem.recorrencia_grupo = grupo
    origem.save(update_fields=['recorrencia_grupo'])

    proxima = _to_date(str(origem.data_competencia))
    for _ in range(11):  # 11 cópias + original = 12 ocorrências
        proxima = delta_fn(proxima)
        Transacao.objects.create(
            descricao=origem.descricao,
            tipo=origem.tipo,
            valor=origem.valor,
            data_competencia=proxima,
            data_vencimento=delta_fn(_to_date(str(origem.data_vencimento))) if origem.data_vencimento else None,
            status='pendente',
            conta_id=origem.conta_id,
            categoria_id=origem.categoria_id,
            cliente_id=origem.cliente_id,
            fornecedor_id=origem.fornecedor_id,
            centro_custo_id=origem.centro_custo_id,
            referencia=origem.referencia,
            observacoes=origem.observacoes,
            recorrencia=rec,
            recorrencia_grupo=grupo,
        )


@login_required
def contas(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = Conta.objects.get(id=rid) if rid else Conta()
            obj.nome = data.get('nome', '').strip()
            obj.banco = data.get('banco', '').strip()
            obj.saldo_inicial = _to_dec(data.get('saldo_inicial', 0))
            obj.ativa = data.get('ativa', True)
            obj.observacoes = data.get('observacoes', '').strip()
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            Conta.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})
    qs = list(Conta.objects.values('id', 'nome', 'banco', 'saldo_inicial', 'ativa', 'observacoes'))
    for c in qs:
        entrada = Transacao.objects.filter(conta_id=c['id'], tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
        saida = Transacao.objects.filter(conta_id=c['id'], tipo='saida', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
        c['saldo_atual'] = float(Decimal(str(c['saldo_inicial'])) + entrada - saida)
        c['saldo_inicial'] = float(c['saldo_inicial'])
    return render(request, 'financeiro/contas.html', {'contas_json': json.dumps(qs)})


@login_required
def categorias(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = Categoria.objects.get(id=rid) if rid else Categoria()
            obj.nome = data.get('nome', '').strip()
            obj.tipo = data.get('tipo', 'ambos')
            pid = data.get('pai_id')
            obj.pai_id = int(pid) if pid else None
            obj.observacoes = data.get('observacoes', '').strip()
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            Categoria.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})
    qs = list(Categoria.objects.values('id', 'nome', 'tipo', 'pai_id', 'observacoes'))
    return render(request, 'financeiro/categorias.html', {'categorias_json': json.dumps(qs)})
