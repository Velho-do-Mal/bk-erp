import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import admin_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q          # ← Q adicionado aqui (era só Sum)
from .models import Conta, Categoria, Transacao, Orcamento
from apps.cadastros.models import Cliente, Fornecedor, CentrosDeCusto

def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, 'empresa', None)




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


@admin_required
def download_anexo(request, pk):
    t = get_object_or_404(Transacao, pk=pk)
    if not t.anexo_dados:
        from django.http import Http404
        raise Http404
    resp = HttpResponse(bytes(t.anexo_dados), content_type=t.anexo_tipo or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{t.anexo_nome}"'
    return resp


@admin_required
def dashboard_financeiro(request):
    from django.db.models.functions import TruncMonth
    from apps.cadastros.models import CentrosDeCusto

    hoje = date.today()

    ini_str = request.GET.get('data_ini', '')
    fim_str = request.GET.get('data_fim', '')
    modo = request.GET.get('modo', 'todos')

    try:
        d_ini = date.fromisoformat(ini_str) if ini_str else date(hoje.year, 1, 1)
    except ValueError:
        d_ini = date(hoje.year, 1, 1)

    try:
        d_fim = date.fromisoformat(fim_str) if fim_str else hoje
    except ValueError:
        d_fim = hoje

    def _qs_base():
        qs = Transacao.objects.filter(empresa=_empresa(request), data_competencia__gte=d_ini, data_competencia__lte=d_fim)
        if modo == 'realizado':
            qs = qs.filter(status='realizado')
        elif modo == 'previsto':
            qs = qs.filter(status='pendente')
        return qs

    total_entrada = Transacao.objects.filter(empresa=_empresa(request), tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    total_saida = Transacao.objects.filter(empresa=_empresa(request), tipo='saida', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    saldo = total_entrada - total_saida
    pendentes_receber = Transacao.objects.filter(empresa=_empresa(request), tipo='entrada', status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    pendentes_pagar = Transacao.objects.filter(empresa=_empresa(request), tipo='saida', status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    ent_periodo = _qs_base().filter(tipo='entrada').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    said_periodo = _qs_base().filter(tipo='saida').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    ultimas = list(Transacao.objects.select_related('categoria', 'conta').order_by('-criado_em')[:10].values(
        'id', 'descricao', 'tipo', 'valor', 'status', 'data_competencia', 'categoria__nome', 'conta__nome'
    ))

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

    keys_sorted = sorted(meses_data.keys())
    acum = 0.0
    for k in keys_sorted:
        acum += meses_data[k].get('entrada', 0) - meses_data[k].get('saida', 0)
        meses_data[k]['acumulado'] = round(acum, 2)

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
        'total_entrada': total_entrada,
        'total_saida': total_saida,
        'saldo': saldo,
        'pendentes_receber': pendentes_receber,
        'pendentes_pagar': pendentes_pagar,
        'ent_periodo': ent_periodo,
        'said_periodo': said_periodo,
        'saldo_periodo': ent_periodo - said_periodo,
        'ultimas_json': json.dumps(ultimas, default=str),
        'meses_json': json.dumps(meses_data),
        'cat_saida_json': json.dumps(cat_saida_data),
        'cc_json': json.dumps(cc_data),
        'data_ini': d_ini.isoformat(),
        'data_fim': d_fim.isoformat(),
        'modo': modo,
    }

    return render(request, 'financeiro/dashboard.html', ctx)


@admin_required
def transacoes(request):
    if request.method == 'POST' and request.FILES.get('anexo'):
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
        obj.recorrencia_parcelas = int(request.POST.get('recorrencia_parcelas') or 0)
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
        if obj.pk is None and _empresa(request):

            obj.empresa = _empresa(request)

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
            obj.recorrencia_parcelas = int(data.get('recorrencia_parcelas') or 0)
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
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            if is_new:
                _gerar_recorrencia(obj)
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            tid  = data.get('id')
            modo = data.get('modo', 'somente_esta')  # somente_esta | proximas | todas

            obj = get_object_or_404(Transacao, id=tid)
            grupo = obj.recorrencia_grupo

            if modo == 'somente_esta' or not grupo:
                obj.delete()
            elif modo == 'proximas':
                # Exclui esta e todas do mesmo grupo com data >= data desta
                Transacao.objects.filter(empresa=_empresa(request), 
                    recorrencia_grupo=grupo,
                    data_competencia__gte=obj.data_competencia
                ).delete()
            elif modo == 'todas':
                Transacao.objects.filter(empresa=_empresa(request), recorrencia_grupo=grupo).delete()
            else:
                obj.delete()

            return JsonResponse({'ok': True})

        elif action == 'toggle_status':
            obj = get_object_or_404(Transacao, id=data.get('id'))
            obj.status = 'realizado' if obj.status == 'pendente' else 'pendente'
            if obj.status == 'realizado' and not obj.data_pagamento:
                obj.data_pagamento = date.today()
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'status': obj.status})

    tipo_f   = request.GET.get('tipo', '')
    status_f = request.GET.get('status', '')
    ini_f    = request.GET.get('data_ini', '')
    fim_f    = request.GET.get('data_fim', '')

    # Se nenhum filtro de período for passado, usa o mês atual como padrão
    hoje = date.today()
    mes_default = hoje.strftime('%Y-%m')
    mes_f = request.GET.get('mes', '')

    # Só aplica default quando nenhum parâmetro de filtro foi enviado na URL
    # (permite que "✕ Limpar" sem parâmetros ainda mostre o mês atual)
    sem_filtro_periodo = not ini_f and not fim_f and not mes_f
    if sem_filtro_periodo:
        mes_f = mes_default

    qs = Transacao.objects.select_related('conta', 'categoria', 'cliente', 'fornecedor', 'centro_custo')

    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if status_f:
        qs = qs.filter(status=status_f)

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
        'conta__nome', 'categoria__nome', 'categoria__pai__nome', 'cliente__nome',
        'fornecedor__nome', 'centro_custo__nome', 'referencia',
        'conta_id', 'categoria_id', 'cliente_id', 'fornecedor_id', 'centro_custo_id',
        'observacoes', 'recorrencia', 'recorrencia_parcelas', 'recorrencia_grupo',
        'anexo_nome', 'anexo_tipo',
    ))

    contas = list(Conta.objects.filter(empresa=_empresa(request), ativa=True).values('id', 'nome'))
    categorias = list(Categoria.objects.filter(empresa=_empresa(request)).values('id', 'nome', 'tipo', 'pai_id'))
    clientes = list(Cliente.objects.filter(empresa=_empresa(request), ativo=True).values('id', 'nome'))
    fornecedores_list = list(Fornecedor.objects.filter(empresa=_empresa(request), ativo=True).values('id', 'nome'))
    centros = list(CentrosDeCusto.objects.filter(empresa=_empresa(request), ativo=True).values('id', 'nome'))

    ctx = {
        'transacoes_json': json.dumps(transacoes_list, default=str),
        'contas_json': json.dumps(contas),
        'categorias_json': json.dumps(categorias),
        'clientes_json': json.dumps(clientes),
        'fornecedores_json': json.dumps(fornecedores_list),
        'centros_json': json.dumps(centros),
        'tipo_f': tipo_f,
        'status_f': status_f,
        'mes_f': mes_f,
        'ini_f': ini_f,
        'fim_f': fim_f,
    }

    return render(request, 'financeiro/transacoes.html', ctx)


def _gerar_recorrencia(origem: Transacao):
    """
    Gera cópias futuras para transações recorrentes.
    - recorrencia_parcelas = 0  → gera 11 repetições (padrão, sem limite definido)
    - recorrencia_parcelas = N  → gera N-1 repetições (N parcelas no total, incluindo a original)
    Exemplos:
      parcelas=3  → origem (1) + 2 cópias  = 3 lançamentos
      parcelas=12 → origem (1) + 11 cópias = 12 lançamentos
      parcelas=0  → origem (1) + 11 cópias = 12 lançamentos (padrão)
    """
    rec = origem.recorrencia
    if not rec or rec not in RECORRENCIA_DELTAS:
        return

    parcelas = int(origem.recorrencia_parcelas or 0)
    # Número de cópias a gerar = parcelas - 1 (a origem já é a 1ª)
    # Se parcelas=0 ou 1, usa padrão de 11 cópias
    n_copias = (parcelas - 1) if parcelas >= 2 else 11

    delta_fn = RECORRENCIA_DELTAS[rec]
    grupo = str(uuid.uuid4())[:8]
    origem.recorrencia_grupo = grupo
    origem.save(update_fields=['recorrencia_grupo'])

    proxima = _to_date(str(origem.data_competencia))
    venc_proxima = _to_date(str(origem.data_vencimento)) if origem.data_vencimento else None

    for i in range(n_copias):
        proxima = delta_fn(proxima)
        if venc_proxima:
            venc_proxima = delta_fn(venc_proxima)
        Transacao.objects.create(
            descricao=origem.descricao,
            tipo=origem.tipo,
            valor=origem.valor,
            data_competencia=proxima,
            data_vencimento=venc_proxima,
            status='pendente',
            conta_id=origem.conta_id,
            categoria_id=origem.categoria_id,
            cliente_id=origem.cliente_id,
            fornecedor_id=origem.fornecedor_id,
            centro_custo_id=origem.centro_custo_id,
            referencia=origem.referencia,
            observacoes=origem.observacoes,
            recorrencia=rec,
            recorrencia_parcelas=origem.recorrencia_parcelas,
            recorrencia_grupo=grupo,
        )


@admin_required
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
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            Conta.objects.filter(empresa=_empresa(request), id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    qs = list(Conta.objects.filter(empresa=_empresa(request)).values('id', 'nome', 'banco', 'saldo_inicial', 'ativa', 'observacoes'))

    for c in qs:
        entrada = Transacao.objects.filter(empresa=_empresa(request), conta_id=c['id'], tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
        saida = Transacao.objects.filter(empresa=_empresa(request), conta_id=c['id'], tipo='saida', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
        c['saldo_atual'] = float(Decimal(str(c['saldo_inicial'])) + entrada - saida)
        c['saldo_inicial'] = float(c['saldo_inicial'])

    return render(request, 'financeiro/contas.html', {'contas_json': json.dumps(qs)})


@admin_required
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
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            Categoria.objects.filter(empresa=_empresa(request), id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    qs = list(Categoria.objects.filter(empresa=_empresa(request)).values('id', 'nome', 'tipo', 'pai_id', 'observacoes'))

    return render(request, 'financeiro/categorias.html', {'categorias_json': json.dumps(qs)})


@admin_required
def orcamento(request):
    from django.db.models.functions import ExtractMonth

    hoje = date.today()
    ano_selecionado = int(request.GET.get('ano', hoje.year))

    # Q já importado no topo do arquivo — sem mais NameError
    # Orçamento: só categorias pai (as subcategorias ficam dentro do pai)
    categorias_entrada = Categoria.objects.filter(Q(tipo='entrada') | Q(tipo='ambos'), empresa=_empresa(request), pai__isnull=True).prefetch_related('subcategorias').order_by('nome')
    categorias_saida = Categoria.objects.filter(Q(tipo='saida') | Q(tipo='ambos'), empresa=_empresa(request), pai__isnull=True).prefetch_related('subcategorias').order_by('nome')

    orcamentos_raw = Orcamento.objects.filter(empresa=_empresa(request), ano=ano_selecionado).values('categoria_id', 'mes', 'valor')

    orc_map = {}
    for o in orcamentos_raw:
        cat_id = o['categoria_id']
        mes = int(o['mes'])
        if cat_id not in orc_map:
            orc_map[cat_id] = {}
        orc_map[cat_id][mes] = float(o['valor'])

    reais_raw = (
        Transacao.objects.filter(empresa=_empresa(request), data_competencia__year=ano_selecionado, status='realizado')
        .annotate(mes_num=ExtractMonth('data_competencia'))
        .values('categoria_id', 'mes_num')
        .annotate(total=Sum('valor'))
    )

    reais_map = {}
    for r in reais_raw:
        cat_id = r['categoria_id']
        mes = int(r['mes_num'])
        if cat_id not in reais_map:
            reais_map[cat_id] = {}
        reais_map[cat_id][mes] = float(r['total'])

    def build_grid(categorias, data_map):
        grid = []
        for cat in categorias:
            meses_valores = [float(data_map.get(cat.id, {}).get(m, 0.0)) for m in range(1, 13)]
            grid.append({
                'id': cat.id,
                'nome': cat.nome,
                'meses': meses_valores,
                'total': sum(meses_valores),
            })
        return grid

    grid_previsto_entrada = build_grid(categorias_entrada, orc_map)
    grid_previsto_saida = build_grid(categorias_saida, orc_map)
    grid_real_entrada = build_grid(categorias_entrada, reais_map)
    grid_real_saida = build_grid(categorias_saida, reais_map)

    totais_previsto = {
        'entrada': [sum(row['meses'][m] for row in grid_previsto_entrada) for m in range(12)],
        'saida': [sum(row['meses'][m] for row in grid_previsto_saida) for m in range(12)],
    }

    totais_real = {
        'entrada': [sum(row['meses'][m] for row in grid_real_entrada) for m in range(12)],
        'saida': [sum(row['meses'][m] for row in grid_real_saida) for m in range(12)],
    }

    fluxo_previsto = []
    fluxo_real = []
    acum_p = 0
    acum_r = 0

    for m in range(12):
        saldo_p = totais_previsto['entrada'][m] - totais_previsto['saida'][m]
        saldo_r = totais_real['entrada'][m] - totais_real['saida'][m]
        acum_p += saldo_p
        acum_r += saldo_r
        fluxo_previsto.append({'mes': m + 1, 'saldo': saldo_p, 'acumulado': acum_p})
        fluxo_real.append({'mes': m + 1, 'saldo': saldo_r, 'acumulado': acum_r})

    ctx = {
        'ano': ano_selecionado,
        'anos_disponiveis': range(hoje.year - 2, hoje.year + 5),
        'grid_previsto_entrada': grid_previsto_entrada,
        'grid_previsto_saida': grid_previsto_saida,
        'grid_real_entrada': grid_real_entrada,
        'grid_real_saida': grid_real_saida,
        'totais_previsto_json': json.dumps(totais_previsto),
        'totais_real_json': json.dumps(totais_real),
        'fluxo_previsto_json': json.dumps(fluxo_previsto),
        'fluxo_real_json': json.dumps(fluxo_real),
    }

    return render(request, 'financeiro/orcamento.html', ctx)


@admin_required
def salvar_orcamento(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cat_id = int(data.get('categoria_id'))
            ano = int(data.get('ano'))
            mes = int(data.get('mes'))
            valor = Decimal(str(data.get('valor', 0)))

            orc, created = Orcamento.objects.update_or_create(
                categoria_id=cat_id, ano=ano, mes=mes,
                defaults={'valor': valor}
            )

            return JsonResponse({'ok': True, 'id': orc.id})

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    return JsonResponse({'ok': False}, status=405)
