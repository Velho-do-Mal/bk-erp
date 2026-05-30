import json
import csv
from datetime import date
from django.shortcuts import render, redirect
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
        # Tenta JSON primeiro (API), depois form data (template)
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        action = data.get('action')

        if action in ('save', 'create', 'criar', 'editar'):
            rid = data.get('id') or data.get('colab_id') or None
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
            if request.content_type and 'json' in request.content_type:
                return JsonResponse({'ok': True, 'id': obj.id})
            return redirect('rh:colaboradores')

        elif action in ('delete', 'excluir'):
            rid = data.get('id') or data.get('colab_id')
            _qs_empresa(Colaborador.objects, request).filter(id=rid).delete()
            if request.content_type and 'json' in request.content_type:
                return JsonResponse({'ok': True})
            return redirect('rh:colaboradores')

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
        # Aceita form data (template) OU JSON (API)
        try:
            data = json.loads(request.body)
            is_json = True
        except Exception:
            data = request.POST
            is_json = False

        action = data.get('action', '')

        if action in ('save', 'criar', 'editar'):
            rid = data.get('id') or data.get('dept_id') or None
            obj = _qs_empresa(Departamento.objects, request).filter(id=rid).first() if rid else Departamento()
            if obj is None:
                obj = Departamento()  # segurança: cria novo se não achar

            obj.nome = data.get('nome', '').strip()
            obj.descricao = data.get('descricao', '').strip()
            # checkbox envia 'on' quando marcado, form data não envia nada quando desmarcado
            if is_json:
                obj.ativo = data.get('ativo', True)
            else:
                obj.ativo = data.get('ativo') == 'on' or data.get('ativo') == 'true' or data.get('ativo') == True

            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()

            if is_json:
                return JsonResponse({'ok': True, 'id': obj.id})
            return redirect('rh:departamentos')

        elif action in ('delete', 'excluir'):
            rid = data.get('id') or data.get('dept_id')
            _qs_empresa(Departamento.objects, request).filter(id=rid).delete()
            if is_json:
                return JsonResponse({'ok': True})
            return redirect('rh:departamentos')

    # GET — passar contexto compatível com o template
    qs = _qs_empresa(Departamento.objects, request).prefetch_related('cargos', 'colaboradores')
    lista = list(qs)

    total_departamentos = len(lista)
    total_ativos = sum(1 for d in lista if d.ativo)
    total_cargos = _qs_empresa(Cargo.objects, request).count()
    total_colaboradores = _qs_empresa(Colaborador.objects, request).filter(status='ativo').count()

    return render(request, 'rh/departamentos.html', {
        'departamentos': lista,
        'deptos_json': json.dumps(
            [{'id': d.id, 'nome': d.nome, 'descricao': d.descricao, 'ativo': d.ativo} for d in lista],
            default=str
        ),
        'total_departamentos': total_departamentos,
        'total_ativos': total_ativos,
        'total_cargos': total_cargos,
        'total_colaboradores': total_colaboradores,
    })


# ── CARGOS ──────────────────────────────────────────────────────────────────

@admin_required
def cargos(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            is_json = True
        except Exception:
            data = request.POST
            is_json = False

        action = data.get('action', '')

        if action in ('save', 'criar', 'editar'):
            rid = data.get('id') or data.get('cargo_id') or None
            obj = _qs_empresa(Cargo.objects, request).filter(id=rid).first() if rid else Cargo()
            if obj is None:
                obj = Cargo()

            obj.nome = data.get('nome', '').strip()
            obj.descricao = data.get('descricao', '').strip()
            obj.salario_base = data.get('salario_base') or 0
            depto_id = data.get('departamento_id')
            obj.departamento_id = int(depto_id) if depto_id else None
            if is_json:
                obj.ativo = data.get('ativo', True)
            else:
                obj.ativo = data.get('ativo') == 'on' or data.get('ativo') == 'true'

            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()

            if is_json:
                return JsonResponse({'ok': True, 'id': obj.id})
            return redirect('rh:cargos')

        elif action in ('delete', 'excluir'):
            rid = data.get('id') or data.get('cargo_id')
            _qs_empresa(Cargo.objects, request).filter(id=rid).delete()
            if is_json:
                return JsonResponse({'ok': True})
            return redirect('rh:cargos')

    lista = list(_qs_empresa(Cargo.objects, request).select_related('departamento'))
    deptos = list(_qs_empresa(Departamento.objects, request).filter(ativo=True).values('id', 'nome'))

    return render(request, 'rh/cargos.html', {
        'cargos': lista,
        'cargos_json': json.dumps(
            [{'id': c.id, 'nome': c.nome, 'descricao': c.descricao,
              'salario_base': float(c.salario_base), 'departamento_id': c.departamento_id,
              'departamento__nome': c.departamento.nome if c.departamento else '',
              'ativo': c.ativo} for c in lista],
            default=str
        ),
        'deptos': deptos,
    })


# ── FÉRIAS ──────────────────────────────────────────────────────────────────

@admin_required
def ferias(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            is_json = True
        except Exception:
            data = request.POST
            is_json = False

        action = data.get('action', '')

        if action in ('save', 'criar', 'editar'):
            rid = data.get('id') or data.get('ferias_id') or None
            obj = _qs_empresa(Ferias.objects, request).filter(id=rid).first() if rid else Ferias()
            if obj is None:
                obj = Ferias()

            colab_id = data.get('colaborador_id')
            obj.colaborador_id = int(colab_id) if colab_id else None
            obj.data_inicio = data.get('data_inicio') or None
            obj.data_fim = data.get('data_fim') or None
            obj.dias = data.get('dias', 30) or 30
            obj.status = data.get('status', 'agendada')
            obj.observacoes = data.get('observacoes', '').strip()
            if obj.pk is None and _empresa(request):
                obj.empresa = _empresa(request)
            obj.save()

            if is_json:
                return JsonResponse({'ok': True, 'id': obj.id})
            return redirect('rh:ferias')

        elif action in ('delete', 'excluir'):
            rid = data.get('id') or data.get('ferias_id')
            _qs_empresa(Ferias.objects, request).filter(id=rid).delete()
            if is_json:
                return JsonResponse({'ok': True})
            return redirect('rh:ferias')

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
