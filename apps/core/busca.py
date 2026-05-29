"""
Busca global — retorna JSON com resultados de múltiplos módulos.
Endpoint: GET /busca/?q=<termo>
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse


def _empresa(request):
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    emp = _empresa(request)
    if emp is None:
        return qs
    return qs.filter(empresa=emp)


@login_required
def busca_global(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': [], 'total': 0})

    resultados = []

    # --- Clientes ---
    try:
        from apps.cadastros.models import Cliente
        clientes = _qs_empresa(Cliente.objects, request).filter(
            Q(nome__icontains=q) | Q(email__icontains=q) | Q(documento__icontains=q)
        )[:5]
        for c in clientes:
            resultados.append({
                'modulo': 'Clientes',
                'icone': 'fas fa-user',
                'cor': '#3b82f6',
                'titulo': c.nome,
                'sub': c.email or c.documento or '',
                'url': reverse('cadastros:clientes'),
            })
    except Exception:
        pass

    # --- Fornecedores ---
    try:
        from apps.cadastros.models import Fornecedor
        fornecedores = _qs_empresa(Fornecedor.objects, request).filter(
            Q(nome__icontains=q) | Q(email__icontains=q) | Q(documento__icontains=q)
        )[:5]
        for f in fornecedores:
            resultados.append({
                'modulo': 'Fornecedores',
                'icone': 'fas fa-building',
                'cor': '#f59e0b',
                'titulo': f.nome,
                'sub': f.email or f.documento or '',
                'url': reverse('cadastros:fornecedores'),
            })
    except Exception:
        pass

    # --- Projetos ---
    try:
        from apps.projetos.models import Projeto
        projetos = _qs_empresa(Projeto.objects, request).filter(
            Q(nome__icontains=q) | Q(descricao__icontains=q) | Q(gerente__icontains=q)
        )[:5]
        for p in projetos:
            resultados.append({
                'modulo': 'Projetos',
                'icone': 'fas fa-project-diagram',
                'cor': '#8b5cf6',
                'titulo': p.nome,
                'sub': f'Gerente: {p.gerente or "—"}',
                'url': reverse('projetos:detalhe', args=[p.pk]),
            })
    except Exception:
        pass

    # --- Documentos ---
    try:
        from apps.documentos.models import Documento
        docs = _qs_empresa(Documento.objects, request).filter(
            Q(nome__icontains=q) | Q(descricao__icontains=q) | Q(tipo__icontains=q)
        )[:5]
        for d in docs:
            resultados.append({
                'modulo': 'Documentos',
                'icone': 'fas fa-file-alt',
                'cor': '#0f766e',
                'titulo': d.nome,
                'sub': d.tipo or '',
                'url': reverse('documentos:lista'),
            })
    except Exception:
        pass

    # --- Transações ---
    try:
        from apps.financeiro.models import Transacao
        trans = _qs_empresa(Transacao.objects, request).filter(
            Q(descricao__icontains=q)
        )[:5]
        for t in trans:
            resultados.append({
                'modulo': 'Financeiro',
                'icone': 'fas fa-dollar-sign',
                'cor': '#16a34a' if t.tipo == 'entrada' else '#dc2626',
                'titulo': t.descricao or '—',
                'sub': f'R$ {t.valor} — {t.data}',
                'url': reverse('financeiro:transacoes'),
            })
    except Exception:
        pass

    # --- Colaboradores (RH) ---
    try:
        from apps.rh.models import Colaborador
        colab = _qs_empresa(Colaborador.objects, request).filter(
            Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(email__icontains=q)
        )[:5]
        for c in colab:
            resultados.append({
                'modulo': 'RH',
                'icone': 'fas fa-id-badge',
                'cor': '#ec4899',
                'titulo': c.nome,
                'sub': c.cargo.nome if c.cargo else 'Sem cargo',
                'url': reverse('rh:colaboradores'),
            })
    except Exception:
        pass

    # --- Pedidos de Compra ---
    try:
        from apps.compras.models import PedidoCompra
        compras = _qs_empresa(PedidoCompra.objects, request).filter(
            Q(numero__icontains=q) | Q(fornecedor__nome__icontains=q)
        )[:3]
        for c in compras:
            resultados.append({
                'modulo': 'Compras',
                'icone': 'fas fa-shopping-cart',
                'cor': '#f97316',
                'titulo': f'Pedido #{c.numero or c.pk}',
                'sub': c.fornecedor.nome if c.fornecedor else '',
                'url': reverse('compras:lista'),
            })
    except Exception:
        pass

    # --- Estoque ---
    try:
        from apps.estoque.models import Produto
        produtos = _qs_empresa(Produto.objects, request).filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )[:3]
        for p in produtos:
            resultados.append({
                'modulo': 'Estoque',
                'icone': 'fas fa-boxes',
                'cor': '#6b7280',
                'titulo': p.nome,
                'sub': f'Código: {p.codigo or "—"}',
                'url': reverse('estoque:lista'),
            })
    except Exception:
        pass

    return JsonResponse({
        'resultados': resultados,
        'total': len(resultados),
        'query': q,
    })
