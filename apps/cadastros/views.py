import json
from apps.core.json_utils import safe_json_dumps
from apps.core.tenant import tenant_get_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.core.exportacao import exportar_csv
from apps.core.audit import registrar as audit
from .models import Cliente, Fornecedor, CentrosDeCusto

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




@login_required
def clientes(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            nome = data.get('nome', '').strip()
            if not nome:
                return JsonResponse({'ok': False, 'error': 'O campo Nome é obrigatório.'})
            rid = data.get('id')
            try:
                obj = tenant_get_or_404(Cliente, request, pk=int(rid)) if rid else Cliente()
            except Cliente.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.nome = nome
            obj.documento = data.get('documento', '').strip()
            obj.email = data.get('email', '').strip()
            obj.telefone = data.get('telefone', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            rid = data.get('id')
            if not rid:
                return JsonResponse({'ok': False, 'error': 'ID não informado.'})
            _qs_empresa(Cliente.objects, request).filter(id=rid).delete()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Ação inválida.'})
    qs = list(_qs_empresa(Cliente.objects, request).filter().values('id', 'nome', 'documento', 'email', 'telefone', 'observacoes', 'ativo'))
    return render(request, 'cadastros/clientes.html', {'clientes_json': safe_json_dumps(qs, ensure_ascii=False)})


@login_required
def fornecedores(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            nome = data.get('nome', '').strip()
            if not nome:
                return JsonResponse({'ok': False, 'error': 'O campo Nome é obrigatório.'})
            rid = data.get('id')
            try:
                obj = tenant_get_or_404(Fornecedor, request, pk=int(rid)) if rid else Fornecedor()
            except Fornecedor.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.nome = nome
            obj.documento = data.get('documento', '').strip()
            obj.email = data.get('email', '').strip()
            obj.telefone = data.get('telefone', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            rid = data.get('id')
            if not rid:
                return JsonResponse({'ok': False, 'error': 'ID não informado.'})
            _qs_empresa(Fornecedor.objects, request).filter(id=rid).delete()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Ação inválida.'})
    qs = list(_qs_empresa(Fornecedor.objects, request).filter().values('id', 'nome', 'documento', 'email', 'telefone', 'observacoes', 'ativo'))
    return render(request, 'cadastros/fornecedores.html', {'fornecedores_json': safe_json_dumps(qs, ensure_ascii=False)})


@login_required
def centros_custo(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            nome = data.get('nome', '').strip()
            if not nome:
                return JsonResponse({'ok': False, 'error': 'O campo Nome é obrigatório.'})
            rid = data.get('id')
            try:
                obj = tenant_get_or_404(CentrosDeCusto, request, pk=int(rid)) if rid else CentrosDeCusto()
            except CentrosDeCusto.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.nome = nome
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            rid = data.get('id')
            if not rid:
                return JsonResponse({'ok': False, 'error': 'ID não informado.'})
            _qs_empresa(CentrosDeCusto.objects, request).filter(id=rid).delete()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Ação inválida.'})
    qs = list(_qs_empresa(CentrosDeCusto.objects, request).filter().values('id', 'nome', 'observacoes', 'ativo'))
    return render(request, 'cadastros/centros_custo.html', {'centros_json': safe_json_dumps(qs, ensure_ascii=False)})


@login_required
def exportar_clientes(request):
    empresa = _empresa(request)
    qs = Cliente.objects.filter(empresa=empresa).values('id', 'nome', 'documento', 'email', 'telefone', 'ativo')
    rows = [list(r.values()) for r in qs]
    return exportar_csv('clientes.csv', ['ID', 'Nome', 'Documento', 'E-mail', 'Telefone', 'Ativo'], rows)


@login_required
def exportar_fornecedores(request):
    empresa = _empresa(request)
    qs = Fornecedor.objects.filter(empresa=empresa).values('id', 'nome', 'cnpj', 'email', 'telefone', 'ativo')
    rows = [list(r.values()) for r in qs]
    return exportar_csv('fornecedores.csv', ['ID', 'Nome', 'CNPJ', 'E-mail', 'Telefone', 'Ativo'], rows)
