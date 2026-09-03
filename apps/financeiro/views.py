import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from apps.core.tenant import tenant_get_or_404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.exportacao import exportar_csv
from apps.core.audit import registrar as audit
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q          # ← Q adicionado aqui (era só Sum)
from .models import Conta, Categoria, Transacao, Orcamento
from apps.cadastros.models import Cliente, Fornecedor, CentrosDeCusto
from apps.rh.models import Colaborador


def _split_favorecido(valor):
    """
    O combobox de favorecido no front-end envia um valor prefixado para
    distinguir Fornecedor de Colaborador (mesmo <select>, duas origens):
    "f-<id>" = fornecedor, "c-<id>" = colaborador, "" = nenhum.
    Retorna (fornecedor_id, colaborador_id) — sempre um dos dois None.
    """
    if not valor:
        return None, None
    valor = str(valor)
    if valor.startswith('f-'):
        return int(valor[2:]), None
    if valor.startswith('c-'):
        return None, int(valor[2:])
    # Compatibilidade com valor legado (só o id do fornecedor, sem prefixo).
    try:
        return int(valor), None
    except (TypeError, ValueError):
        return None, None

def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    """
    Aplica filtro de empresa ao queryset.
    Se empresa for None (superadmin), retorna o queryset sem filtro.
    """
    empresa = _empresa(request)
    if empresa is None:
        return qs
    return qs.filter(empresa=empresa)




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
    from django.http import Http404
    # CORRIGIDO: get_object_or_404 sem filtro de empresa — qualquer usuário
    # logado podia baixar o anexo de uma transação de OUTRA empresa só
    # adivinhando o pk (falta de isolamento de tenant). tenant_get_or_404 é
    # o helper já usado pro resto deste arquivo (ver salvar_transacao etc.)
    # e injeta esse filtro automaticamente.
    t = tenant_get_or_404(Transacao, request, pk=pk)
    if not t.anexo_arquivo:
        raise Http404
    try:
        data = t.anexo_arquivo.read()
    except (FileNotFoundError, OSError):
        # CORRIGIDO: mesma causa do Erro 500 em Documentos — o registro no
        # banco aponta pra um arquivo que não existe mais no storage
        # (local: apagado / perdido num redeploy do filesystem efêmero do
        # Railway sem USE_S3; S3: chave removida do bucket). Antes isso
        # derrubava a página com Erro 500; agora avisa e volta.
        messages.error(
            request,
            f'O anexo "{t.anexo_nome or t.descricao}" não foi encontrado no '
            'armazenamento (pode ter sido removido). Reenvie o anexo ou contate o suporte.'
        )
        return redirect('financeiro:transacoes')
    resp = HttpResponse(data, content_type=t.anexo_tipo or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{t.anexo_nome}"'
    return resp


@login_required
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
        qs = _qs_empresa(Transacao.objects, request).filter(data_competencia__gte=d_ini, data_competencia__lte=d_fim)
        if modo == 'realizado':
            qs = qs.filter(status='realizado')
        elif modo == 'previsto':
            qs = qs.filter(status='pendente')
        return qs

    total_entrada = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    total_saida = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    saldo = total_entrada - total_saida
    pendentes_receber = _qs_empresa(Transacao.objects, request).filter(tipo='entrada', status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    pendentes_pagar = _qs_empresa(Transacao.objects, request).filter(tipo='saida', status='pendente').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    ent_periodo = _qs_base().filter(tipo='entrada').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    said_periodo = _qs_base().filter(tipo='saida').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    ultimas = list(_qs_empresa(Transacao.objects, request).filter().select_related('categoria', 'conta').order_by('-criado_em')[:10].values(
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

    # Contas vencidas detalhadas para o dashboard financeiro
    vencidas_receber = list(
        _qs_empresa(Transacao.objects, request)
        .filter(tipo='entrada', status='pendente', data_vencimento__lt=hoje)
        .order_by('data_vencimento')
        .values('id', 'descricao', 'valor', 'data_vencimento', 'categoria__nome', 'cliente__nome')[:50]
    )
    vencidas_pagar = list(
        _qs_empresa(Transacao.objects, request)
        .filter(tipo='saida', status='pendente', data_vencimento__lt=hoje)
        .order_by('data_vencimento')
        .values('id', 'descricao', 'valor', 'data_vencimento', 'categoria__nome',
                 'fornecedor__nome', 'colaborador__nome')[:50]
    )
    # O favorecido pode ser um Fornecedor OU um Colaborador — mantém a
    # chave 'fornecedor__nome' (já usada pelo JS do dashboard) preenchida
    # com quem estiver definido, para não duplicar a lógica no front-end.
    for v in vencidas_pagar:
        if not v.get('fornecedor__nome') and v.get('colaborador__nome'):
            v['fornecedor__nome'] = v['colaborador__nome']
    total_vencidas_receber = sum(float(v['valor'] or 0) for v in vencidas_receber)
    total_vencidas_pagar   = sum(float(v['valor'] or 0) for v in vencidas_pagar)

    # ── Projeção de Fluxo de Caixa (30/60/90 dias) ──────────────────────
    # Ponto de partida: saldo realizado (entradas - saídas já pagas/recebidas).
    # Para cada horizonte, soma o que já está pendente com vencimento dentro
    # da janela (recebimentos futuros - pagamentos futuros), incluindo o que
    # já está vencido (pendente com vencimento no passado, que ainda deve
    # ser resolvido). Não sintetiza lançamentos recorrentes futuros que
    # ainda não foram gerados — projeta apenas sobre transações já lançadas.
    projecao_fluxo = []
    for horizonte in (30, 60, 90):
        limite = hoje + timedelta(days=horizonte)
        a_receber = _qs_empresa(Transacao.objects, request).filter(
            tipo='entrada', status='pendente', data_vencimento__lte=limite
        ).aggregate(s=Sum('valor'))['s'] or Decimal('0')
        a_pagar = _qs_empresa(Transacao.objects, request).filter(
            tipo='saida', status='pendente', data_vencimento__lte=limite
        ).aggregate(s=Sum('valor'))['s'] or Decimal('0')
        projecao_fluxo.append({
            'dias': horizonte,
            'data_limite': limite.strftime('%d/%m/%Y'),
            'a_receber': float(a_receber),
            'a_pagar': float(a_pagar),
            'saldo_projetado': float(saldo + a_receber - a_pagar),
        })

    ctx = {
        'total_entrada': total_entrada,
        'total_saida': total_saida,
        'saldo': saldo,
        'pendentes_receber': pendentes_receber,
        'pendentes_pagar': pendentes_pagar,
        'ent_periodo': ent_periodo,
        'said_periodo': said_periodo,
        'saldo_periodo': ent_periodo - said_periodo,
        'vencidas_receber_json': json.dumps(vencidas_receber, default=str),
        'vencidas_pagar_json':   json.dumps(vencidas_pagar,   default=str),
        'total_vencidas_receber': total_vencidas_receber,
        'total_vencidas_pagar':   total_vencidas_pagar,
        'ultimas_json': json.dumps(ultimas, default=str),
        'meses_json': json.dumps(meses_data),
        'cat_saida_json': json.dumps(cat_saida_data),
        'cc_json': json.dumps(cc_data),
        'data_ini': d_ini.isoformat(),
        'data_fim': d_fim.isoformat(),
        'modo': modo,
        'projecao_fluxo': projecao_fluxo,
    }

    return render(request, 'financeiro/dashboard.html', ctx)


@login_required
def transacoes(request):
    if request.method == 'POST' and request.FILES.get('anexo'):
        from apps.core.validators import validate_upload_view
        f = request.FILES['anexo']
        err = validate_upload_view(f, 'Anexo')
        if err:
            return JsonResponse({'ok': False, 'erro': err}, status=400)

        rid = request.POST.get('id') or None
        empresa = _empresa(request)
        if rid:
            qs = Transacao.objects.filter(id=int(rid))
            if empresa:
                qs = qs.filter(empresa=empresa)
            obj = get_object_or_404(qs.model, pk=int(rid), **({'empresa': empresa} if empresa else {}))
        else:
            obj = Transacao()
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
        obj.fornecedor_id, obj.colaborador_id = _split_favorecido(request.POST.get('favorecido'))
        ccid = request.POST.get('centro_custo_id')
        obj.centro_custo_id = int(ccid) if ccid else None
        obj.anexo_nome = f.name
        obj.anexo_tipo = f.content_type or 'application/octet-stream'
        obj.anexo_arquivo = f
        if obj.pk is None and empresa:
            obj.empresa = empresa
        obj.save()
        _gerar_recorrencia(obj)
        return JsonResponse({'ok': True, 'id': obj.id})

    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            rid = data.get('id')
            obj = tenant_get_or_404(Transacao, request, pk=int(rid)) if rid else Transacao()
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
            obj.fornecedor_id, obj.colaborador_id = _split_favorecido(data.get('favorecido'))
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

            obj = tenant_get_or_404(Transacao, request, pk=tid)
            grupo = obj.recorrencia_grupo

            if modo == 'somente_esta' or not grupo:
                obj.delete()
            elif modo == 'proximas':
                # Exclui esta e todas do mesmo grupo com data >= data desta
                _qs_empresa(Transacao.objects, request).filter(recorrencia_grupo=grupo,
                    data_competencia__gte=obj.data_competencia
                ).delete()
            elif modo == 'todas':
                _qs_empresa(Transacao.objects, request).filter(recorrencia_grupo=grupo).delete()
            else:
                obj.delete()

            return JsonResponse({'ok': True})

        elif action == 'toggle_status':
            obj = tenant_get_or_404(Transacao, request, pk=data.get('id'))
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

    # CORRIGIDO (segurança): faltava `_qs_empresa` aqui — a listagem de
    # lançamentos financeiros devolvia transações (valor, descrição,
    # cliente/fornecedor) de TODAS as empresas do SaaS pra qualquer
    # usuário logado (vazamento de dados financeiros entre tenants).
    qs = _qs_empresa(Transacao.objects, request).select_related('conta', 'categoria', 'cliente', 'fornecedor', 'colaborador', 'centro_custo')

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
        'fornecedor__nome', 'colaborador__nome', 'centro_custo__nome', 'referencia',
        'conta_id', 'categoria_id', 'cliente_id', 'fornecedor_id', 'colaborador_id', 'centro_custo_id',
        'observacoes', 'recorrencia', 'recorrencia_parcelas', 'recorrencia_grupo',
        'anexo_nome', 'anexo_tipo',
    ))
    # Valor único do combobox de favorecido no front-end (ver
    # _split_favorecido) — evita reimplementar a lógica f-/c- em JS.
    for t in transacoes_list:
        if t.get('fornecedor_id'):
            t['favorecido'] = f"f-{t['fornecedor_id']}"
        elif t.get('colaborador_id'):
            t['favorecido'] = f"c-{t['colaborador_id']}"
        else:
            t['favorecido'] = ''

    contas = list(_qs_empresa(Conta.objects, request).filter(ativa=True).values('id', 'nome'))
    categorias = list(_qs_empresa(Categoria.objects, request).filter().values('id', 'nome', 'tipo', 'pai_id'))
    clientes = list(_qs_empresa(Cliente.objects, request).filter(ativo=True).values('id', 'nome'))
    fornecedores_list = list(_qs_empresa(Fornecedor.objects, request).filter(ativo=True).values('id', 'nome'))
    # Colaboradores entram no mesmo combobox de favorecido que os
    # fornecedores (pedido do usuário) — só os com status "ativo".
    colaboradores_list = list(_qs_empresa(Colaborador.objects, request).filter(status='ativo').values('id', 'nome'))
    centros = list(_qs_empresa(CentrosDeCusto.objects, request).filter(ativo=True).values('id', 'nome'))

    ctx = {
        'transacoes_json': json.dumps(transacoes_list, default=str),
        'contas_json': json.dumps(contas),
        'categorias_json': json.dumps(categorias),
        'clientes_json': json.dumps(clientes),
        'fornecedores_json': json.dumps(fornecedores_list),
        'colaboradores_json': json.dumps(colaboradores_list),
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
            colaborador_id=origem.colaborador_id,
            centro_custo_id=origem.centro_custo_id,
            referencia=origem.referencia,
            observacoes=origem.observacoes,
            recorrencia=rec,
            recorrencia_parcelas=origem.recorrencia_parcelas,
            recorrencia_grupo=grupo,
        )


@login_required
def contas(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            rid = data.get('id')
            # CORRIGIDO (segurança): buscava a Conta só por pk, sem
            # filtro de empresa — um usuário conseguia editar a conta
            # bancária de OUTRA empresa só informando o id dela (IDOR).
            obj = get_object_or_404(_qs_empresa(Conta.objects, request), pk=int(rid)) if rid else Conta()
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
            _qs_empresa(Conta.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    qs = list(_qs_empresa(Conta.objects, request).filter().values('id', 'nome', 'banco', 'saldo_inicial', 'ativa', 'observacoes'))

    for c in qs:
        entrada = _qs_empresa(Transacao.objects, request).filter(conta_id=c['id'], tipo='entrada', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
        saida = _qs_empresa(Transacao.objects, request).filter(conta_id=c['id'], tipo='saida', status='realizado').aggregate(s=Sum('valor'))['s'] or Decimal('0')
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
            # CORRIGIDO (segurança): buscava a Categoria só por pk, sem
            # filtro de empresa — um usuário conseguia editar a categoria
            # de OUTRA empresa só informando o id dela (IDOR).
            obj = get_object_or_404(_qs_empresa(Categoria.objects, request), pk=int(rid)) if rid else Categoria()
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
            _qs_empresa(Categoria.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    qs = list(_qs_empresa(Categoria.objects, request).filter().values('id', 'nome', 'tipo', 'pai_id', 'observacoes'))

    return render(request, 'financeiro/categorias.html', {'categorias_json': json.dumps(qs)})


@login_required
def orcamento(request):
    from django.db.models.functions import ExtractMonth

    hoje = date.today()
    ano_selecionado = int(request.GET.get('ano', hoje.year))

    # Q já importado no topo do arquivo — sem mais NameError
    # Orçamento: só categorias pai (as subcategorias ficam dentro do pai)
    categorias_entrada = Categoria.objects.filter(Q(tipo='entrada') | Q(tipo='ambos'), empresa=_empresa(request), pai__isnull=True).prefetch_related('subcategorias').order_by('nome')
    categorias_saida = Categoria.objects.filter(Q(tipo='saida') | Q(tipo='ambos'), empresa=_empresa(request), pai__isnull=True).prefetch_related('subcategorias').order_by('nome')

    orcamentos_raw = _qs_empresa(Orcamento.objects, request).filter(ano=ano_selecionado).values('categoria_id', 'mes', 'valor')

    orc_map = {}
    for o in orcamentos_raw:
        cat_id = o['categoria_id']
        mes = int(o['mes'])
        if cat_id not in orc_map:
            orc_map[cat_id] = {}
        orc_map[cat_id][mes] = float(o['valor'])

    reais_raw = (
        _qs_empresa(Transacao.objects, request).filter(data_competencia__year=ano_selecionado, status='realizado')
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


@login_required
def salvar_orcamento(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cat_id = int(data.get('categoria_id'))
            ano = int(data.get('ano'))
            mes = int(data.get('mes'))
            valor = Decimal(str(data.get('valor', 0)))

            # CORRIGIDO (segurança): não validava que a categoria
            # pertence à empresa do usuário nem gravava o orçamento com
            # a empresa correta — um usuário conseguia criar/alterar
            # orçamento de uma categoria de OUTRA empresa só informando
            # o id dela (IDOR de escrita).
            categoria = get_object_or_404(_qs_empresa(Categoria.objects, request), pk=cat_id)

            orc, created = Orcamento.objects.update_or_create(
                categoria=categoria, ano=ano, mes=mes,
                # empresa vem da categoria (já validada acima), não do
                # request — evita zerar o campo se um superadmin editar.
                defaults={'valor': valor, 'empresa': categoria.empresa}
            )

            return JsonResponse({'ok': True, 'id': orc.id})

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    return JsonResponse({'ok': False}, status=405)


@login_required
def exportar_transacoes(request):
    # CORRIGIDO: .values(..., 'data', ...) — Transacao não tem campo
    # chamado "data" (os campos reais são data_competencia,
    # data_vencimento, data_pagamento), então o Django lançava FieldError
    # e a rota dava Erro 500 sempre que alguém clicava em "Exportar CSV"
    # em Financeiro (mesma classe de bug já corrigida em
    # vendas.exportar_propostas — ver histórico). Usa data_competencia,
    # que é o campo obrigatório (sempre preenchido) e é o que a tela de
    # Financeiro mostra como "Data" nas listagens.
    # Também trocado o filtro manual empresa=empresa por _qs_empresa(),
    # que já trata corretamente o caso do superadmin (empresa=None não
    # deve filtrar nada, e sim ver tudo).
    qs = _qs_empresa(Transacao.objects, request).values_list(
        'id', 'descricao', 'tipo', 'valor', 'data_competencia', 'categoria__nome', 'conta__nome'
    )
    rows = [
        [id_, descricao, tipo, float(valor), data.strftime('%d/%m/%Y') if data else '', categoria, conta]
        for id_, descricao, tipo, valor, data, categoria, conta in qs
    ]
    return exportar_csv('transacoes.csv', ['ID', 'Descrição', 'Tipo', 'Valor', 'Data', 'Categoria', 'Conta'], rows)
