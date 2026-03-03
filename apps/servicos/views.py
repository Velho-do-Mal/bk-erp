import json
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ProdutoServico


@login_required
def lista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            rid = data.get('id')
            obj = ProdutoServico.objects.get(id=rid) if rid else ProdutoServico()
            obj.codigo = data.get('codigo', '').strip()
            obj.tipo = data.get('tipo', 'servico')
            obj.nome = data.get('nome', '').strip()
            obj.descricao = data.get('descricao', '').strip()
            obj.unidade = data.get('unidade', 'un').strip()
            try:
                obj.preco_unitario = Decimal(str(data.get('preco_unitario', 0) or 0))
            except Exception:
                obj.preco_unitario = Decimal('0')
            obj.ativo = data.get('ativo', True)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            ProdutoServico.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'toggle_ativo':
            obj = ProdutoServico.objects.get(id=data.get('id'))
            obj.ativo = not obj.ativo
            obj.save()
            return JsonResponse({'ok': True, 'ativo': obj.ativo})

    items = list(ProdutoServico.objects.values(
        'id', 'codigo', 'tipo', 'nome', 'descricao', 'unidade', 'preco_unitario', 'ativo'
    ))
    for i in items:
        i['preco_unitario'] = float(i['preco_unitario'])

    return render(request, 'servicos/lista.html', {
        'items_json': json.dumps(items),
        'total': ProdutoServico.objects.count(),
        'ativos': ProdutoServico.objects.filter(ativo=True).count(),
    })
