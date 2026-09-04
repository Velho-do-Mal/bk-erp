import json
from apps.core.json_utils import safe_json_dumps
from decimal import Decimal
from datetime import date
from apps.core.tenant import tenant_get_or_404
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.core.exportacao import exportar_csv
from apps.core.audit import registrar as audit
from django.http import JsonResponse
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from .models import MaterialEstoque
from apps.cadastros.models import Fornecedor, CentrosDeCusto

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


@login_required
def lista(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            descricao = data.get('descricao', '').strip()
            if not descricao:
                return JsonResponse({'ok': False, 'error': 'O campo Descrição é obrigatório.'})
            rid = data.get('id')
            try:
                obj = tenant_get_or_404(MaterialEstoque, request, pk=int(rid)) if rid else MaterialEstoque()
            except MaterialEstoque.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Registro não encontrado.'})
            obj.codigo = data.get('codigo', '').strip()
            obj.tipo = data.get('tipo') or 'material'
            obj.descricao = descricao
            fid = data.get('fornecedor_id')
            obj.fornecedor_id = int(fid) if fid else None
            ccid = data.get('centro_custo_id')
            obj.centro_custo_id = int(ccid) if ccid else None
            obj.qtd_comprada = _to_dec(data.get('qtd_comprada', 0))
            obj.preco_total = _to_dec(data.get('preco_total', 0))
            # Calcula preço unitário
            if obj.qtd_comprada and obj.preco_total:
                obj.preco_unitario = obj.preco_total / obj.qtd_comprada
            obj.data_compra = _to_date(data.get('data_compra'))
            obj.data_validade = _to_date(data.get('data_validade'))
            obj.observacoes = data.get('observacoes', '').strip()
            if obj.pk is None and _empresa(request):

                obj.empresa = _empresa(request)

            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'save_utilizado':
            # Atualiza apenas qtd_utilizada (tabela inline)
            updates = data.get('updates', [])
            for u in updates:
                _qs_empresa(MaterialEstoque.objects, request).filter(id=u['id']).update(
                    qtd_utilizada=_to_dec(u['qtd_utilizada'])
                )
            return JsonResponse({'ok': True, 'n': len(updates)})

        elif action == 'delete':
            rid = data.get('id')
            if not rid:
                return JsonResponse({'ok': False, 'error': 'ID não informado.'})
            _qs_empresa(MaterialEstoque.objects, request).filter(id=rid).delete()
            return JsonResponse({'ok': True})

    qs = _qs_empresa(MaterialEstoque.objects, request).select_related('fornecedor', 'centro_custo', 'pedido_origem')
    materiais = []
    for m in qs:
        materiais.append({
            'id': m.id,
            'codigo': m.codigo,
            'tipo': m.tipo,
            'tipo_label': m.get_tipo_display(),
            'descricao': m.descricao,
            'fornecedor_id': m.fornecedor_id,
            'fornecedor_nome': m.fornecedor.nome if m.fornecedor else '',
            'centro_custo_id': m.centro_custo_id,
            'centro_custo_nome': m.centro_custo.nome if m.centro_custo else '',
            'projeto_nome': m.projeto_nome,
            'qtd_comprada': float(m.qtd_comprada),
            'qtd_utilizada': float(m.qtd_utilizada),
            'saldo': float(m.saldo),
            'preco_unitario': float(m.preco_unitario),
            'preco_total': float(m.preco_total),
            'data_compra': m.data_compra.isoformat() if m.data_compra else '',
            'data_validade': m.data_validade.isoformat() if m.data_validade else '',
            'observacoes': m.observacoes,
            'pedido_origem_id': m.pedido_origem_id,
        })

    total_investido = sum(m['preco_total'] for m in materiais)
    total_itens = len(materiais)
    itens_criticos = sum(1 for m in materiais if m['saldo'] <= 0)
    # Alerta de estoque baixo: saldo positivo mas abaixo de 10% da quantidade
    # comprada (sem campo de "estoque mínimo" configurável no modelo — usa
    # uma heurística proporcional para sinalizar itens que estão acabando).
    itens_estoque_baixo = sum(
        1 for m in materiais
        if m['saldo'] > 0 and m['qtd_comprada'] > 0 and (m['saldo'] / m['qtd_comprada']) <= 0.10
    )

    ctx = {
        'materiais_json': safe_json_dumps(materiais),
        'fornecedores': list(_qs_empresa(Fornecedor.objects, request).filter(ativo=True).values('id', 'nome')),
        'centros_custo': list(_qs_empresa(CentrosDeCusto.objects, request).filter(ativo=True).values('id', 'nome')),
        'total_investido': total_investido,
        'total_itens': total_itens,
        'itens_criticos': itens_criticos,
        'itens_estoque_baixo': itens_estoque_baixo,
        'tipos_material': MaterialEstoque.TIPO_CHOICES,
    }
    return render(request, 'estoque/lista.html', ctx)


@login_required
def exportar_estoque(request):
    # CORRIGIDO: a query anterior referenciava campos inexistentes no modelo
    # (codigo_bk, unidade, qtd_saldo) e sempre lançava FieldError ao ser chamada.
    qs = _qs_empresa(MaterialEstoque.objects, request).annotate(
        qtd_saldo=F('qtd_comprada') - F('qtd_utilizada')
    ).values('id', 'codigo', 'tipo', 'descricao', 'qtd_comprada', 'qtd_utilizada', 'qtd_saldo')
    rows = [list(r.values()) for r in qs]
    return exportar_csv(
        'estoque.csv',
        ['ID', 'Código', 'Tipo', 'Descrição', 'Qtd Comprada', 'Qtd Utilizada', 'Saldo'],
        rows,
    )
