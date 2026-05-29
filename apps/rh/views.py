import json
import csv
from datetime import date
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import admin_required
from .models import Colaborador, Cargo, Departamento, Ferias


def _empresa(request):
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    empresa = _empresa(request)
    if empresa is None:
        return qs
    return qs.filter(empresa=empresa)


# ── COLABORADORES ──────────────────────────────────────────────────────────

@admin_required
def colaboradores(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
        action = data.get('action')

        if action in ('save', 'create'):
            rid = data.get('id')
            obj = _qs_empresa(Colaborador.objects, request).filter(id=rid).first() if rid else Colaborador()
            if obj is None:
                return JsonResponse({'ok': False, 'error': 'Não encontrado'}, status=404)

            obj.nome = data.get('nome', '').strip()
            obj.cpf = data.get('cpf', '').strip()
            obj.rg = data.get('rg', '').strip()
            obj.data_nascimento = data.get('data_nascimento') or None
            obj.sexo = data.get('sexo', '')
            obj.estado_civil = data.get('estado_civil', '')
            obj.email = data.get('email', '').strip()
            obj.telefone = data.get('telefone', '').strip()
            obj.endereco = data.get('endereco', '').strip()
            obj.cep = data.get('cep', '').strip()
            obj.cidade = data.get('cidade', '').strip()
            obj.estado = data.get('estado', '').strip()
            obj.matricula = data.get('matricula', '').strip()
            cargo_id = data.get('cargo_id')
            obj.cargo_id = int(cargo_id) if cargo_id else None
            depto_id = data.get('departamento_id')
            obj.departamento_id = int(depto_id) if depto_id else None
            obj.regime = data.get('regime', 'clt')
            obj.data_admissao = data.get('data_admissao') or None
            obj.data_demissao = data.get('data_demissao') or None
            obj.salario = data.get('salario') or 0
            obj.status = data.get('status', 'ativo')
            obj.banco = data.get('banco', '').strip()
            obj.agencia = data.get('agencia', '').strip()
            obj.conta = data.get('conta', '').strip()
            obj.pix = data.get('pix', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            _qs_empresa(Colaborador.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    # GET
    status_f = request.GET.get('status', '')
    depto_f = request.GET.get('depto', '')
    q = request.GET.get('q', '')

    qs = _qs_empresa(Colaborador.objects, request).select_related('cargo', 'departamento')
    if status_f:
        qs = qs.filter(status=status_f)
    if depto_f:
        qs = qs.filter(departamento_id=depto_f)
    if q:
        qs = qs.filter(nome__icontains=q)

    lista = list(qs.values(
        'id', 'nome', 'cpf', 'rg', 'data_nascimento', 'sexo', 'estado_civil',
        'email', 'telefone', 'endereco', 'cep', 'cidade', 'estado',
        'matricula', 'cargo__nome', 'cargo_id', 'departamento__nome', 'departamento_id',
        'regime', 'data_admissao', 'data_demissao', 'salario', 'status',
        'banco', 'agencia', 'conta', 'pix', 'observacoes',
    ))

    deptos = list(_qs_empresa(Departamento.objects, request).filter(ativo=True).values('id', 'nome'))
    cargos = list(_qs_empresa(Cargo.objects, request).filter(ativo=True).values('id', 'nome', 'departamento_id'))

    # KPIs
    total = _qs_empresa(Colaborador.objects, request).count()
    ativos = _qs_empresa(Colaborador.objects, request).filter(status='ativo').count()
    em_ferias = _qs_empresa(Colaborador.objects, request).filter(status='ferias').count()
    desligados = _qs_empresa(Colaborador.objects, request).filter(status='desligado').count()

    return render(request, 'rh/colaboradores.html', {
        'colaboradores_json': json.dumps(lista, default=str),
        'deptos': deptos,
        'cargos': cargos,
        'status_f': status_f,
        'depto_f': depto_f,
        'q': q,
        'kpi_total': total,
        'kpi_ativos': ativos,
        'kpi_ferias': em_ferias,
        'kpi_desligados': desligados,
    })


@admin_required
def exportar_colaboradores(request):
    qs = _qs_empresa(Colaborador.objects, request).select_related('cargo', 'departamento').order_by('nome')
    resp = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    resp['Content-Disposition'] = 'attachment; filename="colaboradores.csv"'
    w = csv.writer(resp, delimiter=';')
    w.writerow(['Nome', 'CPF', 'E-mail', 'Telefone', 'Cargo', 'Departamento',
                'Regime', 'Admissão', 'Salário', 'Status'])
    for c in qs:
        w.writerow([c.nome, c.cpf, c.email, c.telefone,
                    c.cargo.nome if c.cargo else '', c.departamento.nome if c.departamento else '',
                    c.get_regime_display(), c.data_admissao or '', float(c.salario), c.get_status_display()])
    return resp


# ── DEPARTAMENTOS ──────────────────────────────────────────────────────────

@admin_required
def departamentos(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = _qs_empresa(Departamento.objects, request).filter(id=rid).first() if rid else Departamento()
            if obj is None:
                return JsonResponse({'ok': False, 'error': 'Não encontrado'}, status=404)
            obj.nome = data.get('nome', '').strip()
            obj.descricao = data.get('descricao', '').strip()
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            _qs_empresa(Departamento.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    lista = list(_qs_empresa(Departamento.objects, request).values('id', 'nome', 'descricao', 'ativo'))
    for d in lista:
        d['total_colaboradores'] = Colaborador.objects.filter(departamento_id=d['id'], status='ativo').count()

    return render(request, 'rh/departamentos.html', {
        'deptos_json': json.dumps(lista, default=str),
    })


# ── CARGOS ──────────────────────────────────────────────────────────────────

@admin_required
def cargos(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = _qs_empresa(Cargo.objects, request).filter(id=rid).first() if rid else Cargo()
            if obj is None:
                return JsonResponse({'ok': False, 'error': 'Não encontrado'}, status=404)
            obj.nome = data.get('nome', '').strip()
            obj.descricao = data.get('descricao', '').strip()
            obj.salario_base = data.get('salario_base') or 0
            depto_id = data.get('departamento_id')
            obj.departamento_id = int(depto_id) if depto_id else None
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            _qs_empresa(Cargo.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    lista = list(_qs_empresa(Cargo.objects, request).select_related('departamento').values(
        'id', 'nome', 'descricao', 'salario_base', 'departamento__nome', 'departamento_id', 'ativo'
    ))
    deptos = list(_qs_empresa(Departamento.objects, request).filter(ativo=True).values('id', 'nome'))
    return render(request, 'rh/cargos.html', {
        'cargos_json': json.dumps(lista, default=str),
        'deptos': deptos,
    })


# ── FÉRIAS ──────────────────────────────────────────────────────────────────

@admin_required
def ferias(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = _qs_empresa(Ferias.objects, request).filter(id=rid).first() if rid else Ferias()
            if obj is None:
                return JsonResponse({'ok': False, 'error': 'Não encontrado'}, status=404)
            colab_id = data.get('colaborador_id')
            obj.colaborador_id = int(colab_id) if colab_id else None
            obj.data_inicio = data.get('data_inicio')
            obj.data_fim = data.get('data_fim')
            obj.dias = data.get('dias', 30)
            obj.status = data.get('status', 'agendada')
            obj.observacoes = data.get('observacoes', '').strip()
            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            _qs_empresa(Ferias.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    lista = list(_qs_empresa(Ferias.objects, request).select_related('colaborador').values(
        'id', 'colaborador__nome', 'colaborador_id', 'data_inicio', 'data_fim', 'dias', 'status', 'observacoes'
    ))
    colaboradores_list = list(_qs_empresa(Colaborador.objects, request).filter(
        status__in=['ativo', 'ferias']
    ).values('id', 'nome'))

    return render(request, 'rh/ferias.html', {
        'ferias_json': json.dumps(lista, default=str),
        'colaboradores': colaboradores_list,
    })
