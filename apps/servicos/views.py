import json
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse
from apps.accounts.decorators import admin_required
from .models import ProdutoServico

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




@admin_required
def lista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            nome = data.get('nome', '').strip()
            if not nome:
                return JsonResponse({'ok': False, 'error': 'O campo Nome é obrigatório.'})
            rid = data.get('id')
            try:
                obj = ProdutoServico.objects.get(id=rid) if rid else ProdutoServico()
            except ProdutoServico.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.codigo = data.get('codigo', '').strip()
            obj.tipo = data.get('tipo', 'servico')
            obj.nome = nome
            obj.descricao = data.get('descricao', '').strip()
            obj.unidade = data.get('unidade', 'un').strip() or 'un'
            try:
                obj.preco_unitario = Decimal(str(data.get('preco_unitario', 0) or 0))
            except Exception:
                obj.preco_unitario = Decimal('0')
            obj.ativo = data.get('ativo', True)
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            rid = data.get('id')
            if not rid:
                return JsonResponse({'ok': False, 'error': 'ID não informado.'})
            _qs_empresa(ProdutoServico.objects, request).filter(id=rid).delete()
            return JsonResponse({'ok': True})

        elif action == 'toggle_ativo':
            try:
                obj = ProdutoServico.objects.get(id=data.get('id'))
            except ProdutoServico.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.ativo = not obj.ativo
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'ativo': obj.ativo})

        return JsonResponse({'ok': False, 'error': 'Ação inválida.'})

    items = list(_qs_empresa(ProdutoServico.objects, request).filter().values(
        'id', 'codigo', 'tipo', 'nome', 'descricao', 'unidade', 'preco_unitario', 'ativo'
    ))
    for i in items:
        i['preco_unitario'] = float(i['preco_unitario'])

    return render(request, 'servicos/lista.html', {
        'items_json': json.dumps(items, ensure_ascii=False),
        'total': ProdutoServico.objects.count(),
        'ativos': _qs_empresa(ProdutoServico.objects, request).filter(ativo=True).count(),
    })
