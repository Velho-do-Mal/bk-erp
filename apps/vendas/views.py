import json
from decimal import Decimal
from datetime import date
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from .models import Proposta, ItemProposta, Lead
from apps.cadastros.models import Cliente


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
    # ── Propostas POST ──────────────────────────────
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save_proposta':
            rid = data.get('id')
            obj = Proposta.objects.get(id=rid) if rid else Proposta()
            obj.codigo = data.get('codigo', '').strip()
            obj.titulo = data.get('titulo', '').strip()
            cid = data.get('cliente_id')
            obj.cliente_id = int(cid) if cid else None
            obj.projeto_nome = data.get('projeto_nome', '').strip()
            obj.data_emissao = _to_date(data.get('data_emissao')) or date.today()
            obj.data_validade = _to_date(data.get('data_validade'))
            obj.status = data.get('status', 'rascunho')
            obj.condicoes_pagamento = data.get('condicoes_pagamento', '').strip()
            obj.prazo_execucao = data.get('prazo_execucao', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.notas_tecnicas = data.get('notas_tecnicas', '').strip()
            obj.save()

            # Salva itens
            itens = data.get('itens', [])
            obj.itens.all().delete()
            total = Decimal('0')
            for i, it in enumerate(itens):
                qty = _to_dec(it.get('quantidade', 1))
                preco = _to_dec(it.get('preco_unitario', 0))
                subtotal = qty * preco
                total += subtotal
                ItemProposta.objects.create(
                    proposta=obj,
                    descricao=it.get('descricao', ''),
                    unidade=it.get('unidade', ''),
                    quantidade=qty,
                    preco_unitario=preco,
                    preco_total=subtotal,
                    ordem=i,
                )
            obj.valor_total = total
            obj.save(update_fields=['valor_total'])
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete_proposta':
            Proposta.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'gerar_financeiro':
            prop = get_object_or_404(Proposta, id=data.get('id'))
            ref = f"PROP:{prop.id}"
            try:
                from apps.financeiro.models import Transacao
                if Transacao.objects.filter(referencia=ref).exists():
                    return JsonResponse({'ok': False, 'msg': 'Já existe lançamento para esta proposta.'})
                t = Transacao.objects.create(
                    descricao=f"Proposta {prop.codigo} — {prop.titulo}",
                    tipo='entrada',
                    valor=prop.valor_total,
                    data_competencia=prop.data_emissao,
                    data_vencimento=prop.data_validade,
                    status='pendente',
                    cliente_id=prop.cliente_id,
                    referencia=ref,
                    observacoes=f"Gerado automaticamente da proposta {prop.codigo}",
                )
                prop.transacao_financeiro_ref = ref
                prop.save(update_fields=['transacao_financeiro_ref'])
                return JsonResponse({'ok': True, 'msg': f'Conta a receber criada (ID {t.id})'})
            except Exception as e:
                return JsonResponse({'ok': False, 'msg': str(e)})

        elif action == 'save_lead':
            rid = data.get('id')
            obj = Lead.objects.get(id=rid) if rid else Lead()
            obj.nome = data.get('nome', '').strip()
            obj.empresa = data.get('empresa', '').strip()
            obj.contato = data.get('contato', '').strip()
            obj.email = data.get('email', '').strip()
            obj.estagio = data.get('estagio', 'prospeccao')
            obj.valor_estimado = _to_dec(data.get('valor_estimado', 0))
            obj.observacoes = data.get('observacoes', '').strip()
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        elif action == 'delete_lead':
            Lead.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'get_proposta':
            pid = data.get('id')
            try:
                p = Proposta.objects.select_related('cliente').get(id=pid)
                itens_qs = p.itens.all()
                itens_data = [{
                    'descricao': it.descricao,
                    'unidade': it.unidade,
                    'quantidade': float(it.quantidade),
                    'preco_unitario': float(it.preco_unitario),
                    'preco_total': float(it.preco_total),
                } for it in itens_qs]
                prop_data = {
                    'id': p.id,
                    'codigo': p.codigo,
                    'titulo': p.titulo,
                    'cliente_nome': p.cliente.nome if p.cliente else '',
                    'data_emissao': str(p.data_emissao) if p.data_emissao else '',
                    'data_validade': str(p.data_validade) if p.data_validade else '',
                    'valor_total': float(p.valor_total),
                    'objetivo': '',
                    'escopo': p.notas_tecnicas or '',
                    'observacoes': p.observacoes or '',
                    'condicoes_pagamento': p.condicoes_pagamento or '',
                    'prazo_entrega': p.prazo_execucao or '',
                    'referencia': p.projeto_nome or '',
                }
                return JsonResponse({'ok': True, 'proposta': prop_data, 'itens': itens_data})
            except Exception as e:
                return JsonResponse({'ok': False, 'erro': str(e)})

    # GET
    propostas = Proposta.objects.select_related('cliente').prefetch_related('itens')
    propostas_data = []
    for p in propostas:
        propostas_data.append({
            'id': p.id,
            'codigo': p.codigo,
            'titulo': p.titulo,
            'cliente_id': p.cliente_id,
            'cliente_nome': p.cliente.nome if p.cliente else '',
            'projeto_nome': p.projeto_nome,
            'data_emissao': p.data_emissao.isoformat() if p.data_emissao else '',
            'data_validade': p.data_validade.isoformat() if p.data_validade else '',
            'status': p.status,
            'valor_total': float(p.valor_total),
            'condicoes_pagamento': p.condicoes_pagamento,
            'prazo_execucao': p.prazo_execucao,
            'observacoes': p.observacoes,
            'notas_tecnicas': p.notas_tecnicas,
            'tem_financeiro': bool(p.transacao_financeiro_ref),
            'itens': [
                {'descricao': it.descricao, 'unidade': it.unidade,
                 'quantidade': float(it.quantidade), 'preco_unitario': float(it.preco_unitario),
                 'preco_total': float(it.preco_total)}
                for it in p.itens.all()
            ],
        })

    leads_data = list(Lead.objects.values(
        'id', 'nome', 'empresa', 'contato', 'email', 'estagio', 'valor_estimado', 'observacoes'
    ))
    for l in leads_data:
        l['valor_estimado'] = float(l['valor_estimado'])

    # KPIs
    total_valor = Proposta.objects.aggregate(s=Sum('valor_total'))['s'] or 0
    aprovadas = Proposta.objects.filter(status='aprovada').count()
    pipeline_valor = Lead.objects.filter(
        estagio__in=['qualificacao', 'proposta', 'negociacao']
    ).aggregate(s=Sum('valor_estimado'))['s'] or 0

    ctx = {
        'propostas_json': json.dumps(propostas_data),
        'leads_json': json.dumps(leads_data, default=str),
        'clientes': list(Cliente.objects.filter(ativo=True).values('id', 'nome')),
        'total_propostas': Proposta.objects.count(),
        'total_valor': float(total_valor),
        'aprovadas': aprovadas,
        'pipeline_valor': float(pipeline_valor),
    }
    return render(request, 'vendas/lista.html', ctx)
