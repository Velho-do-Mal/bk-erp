import json
from decimal import Decimal
from datetime import date
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from .models import PedidoCompra, ItemPedidoCompra
from apps.cadastros.models import Fornecedor


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


@login_required
def lista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            rid = data.get('id')
            obj = PedidoCompra.objects.get(id=rid) if rid else PedidoCompra()
            obj.codigo = data.get('codigo', '').strip()
            fid = data.get('fornecedor_id')
            obj.fornecedor_id = int(fid) if fid else None
            obj.projeto_nome = data.get('projeto_nome', '').strip()
            obj.data_pedido = _to_date(data.get('data_pedido')) or date.today()
            obj.data_entrega_prevista = _to_date(data.get('data_entrega_prevista'))
            obj.data_entrega_real = _to_date(data.get('data_entrega_real'))
            obj.status = data.get('status', 'aberta')
            obj.observacoes = data.get('observacoes', '').strip()
            obj.save()

            # Salva itens
            itens = data.get('itens', [])
            obj.itens.all().delete()
            total = Decimal('0')
            for it in itens:
                qty = _to_dec(it.get('quantidade', 1))
                preco = _to_dec(it.get('preco_unitario', 0))
                subtotal = qty * preco
                total += subtotal
                ItemPedidoCompra.objects.create(
                    pedido=obj,
                    descricao=it.get('descricao', ''),
                    codigo_material=it.get('codigo_material', ''),
                    unidade=it.get('unidade', ''),
                    quantidade=qty,
                    preco_unitario=preco,
                    preco_total=subtotal,
                )
            obj.valor_total = total
            obj.save(update_fields=['valor_total'])
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete':
            PedidoCompra.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'gerar_financeiro':
            # Cria conta a pagar no Financeiro
            po = get_object_or_404(PedidoCompra, id=data.get('id'))
            ref = f"PC:{po.id}"
            try:
                from apps.financeiro.models import Transacao
                if Transacao.objects.filter(referencia=ref).exists():
                    return JsonResponse({'ok': False, 'msg': 'Já existe lançamento para este pedido.'})
                t = Transacao.objects.create(
                    descricao=f"Pedido de Compra {po.codigo}",
                    tipo='saida',
                    valor=po.valor_total,
                    data_competencia=po.data_pedido,
                    data_vencimento=po.data_entrega_prevista,
                    status='pendente',
                    fornecedor_id=po.fornecedor_id,
                    referencia=ref,
                    observacoes=f"Gerado automaticamente a partir do PC {po.codigo}",
                )
                po.transacao_financeiro_ref = ref
                po.save(update_fields=['transacao_financeiro_ref'])
                return JsonResponse({'ok': True, 'msg': f'Conta a pagar criada (ID {t.id})'})
            except Exception as e:
                return JsonResponse({'ok': False, 'msg': str(e)})

    # GET - lista pedidos
    pedidos = PedidoCompra.objects.select_related('fornecedor').prefetch_related('itens')
    pedidos_data = []
    for p in pedidos:
        pedidos_data.append({
            'id': p.id,
            'codigo': p.codigo,
            'fornecedor_id': p.fornecedor_id,
            'fornecedor_nome': p.fornecedor.nome if p.fornecedor else '',
            'projeto_nome': p.projeto_nome,
            'data_pedido': p.data_pedido.isoformat() if p.data_pedido else '',
            'data_entrega_prevista': p.data_entrega_prevista.isoformat() if p.data_entrega_prevista else '',
            'data_entrega_real': p.data_entrega_real.isoformat() if p.data_entrega_real else '',
            'valor_total': float(p.valor_total),
            'status': p.status,
            'observacoes': p.observacoes,
            'tem_financeiro': bool(p.transacao_financeiro_ref),
            'itens': [
                {
                    'descricao': it.descricao,
                    'codigo_material': it.codigo_material,
                    'unidade': it.unidade,
                    'quantidade': float(it.quantidade),
                    'preco_unitario': float(it.preco_unitario),
                    'preco_total': float(it.preco_total),
                }
                for it in p.itens.all()
            ],
        })

    # KPIs
    qs = PedidoCompra.objects
    total_valor = qs.aggregate(s=Sum('valor_total'))['s'] or 0
    em_aberto = qs.filter(status__in=['aberta', 'aprovacao', 'aprovada']).count()
    canceladas = qs.filter(status='cancelada').count()

    ctx = {
        'pedidos_json': json.dumps(pedidos_data),
        'fornecedores': list(Fornecedor.objects.filter(ativo=True).values('id', 'nome')),
        'total_pedidos': qs.count(),
        'total_valor': float(total_valor),
        'em_aberto': em_aberto,
        'canceladas': canceladas,
    }
    return render(request, 'compras/lista.html', ctx)
