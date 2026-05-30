"""
tenant.py — Helpers para isolamento seguro de tenant (empresa).
Garante que consultas por PK sempre incluam filtro de empresa.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404 as _goo404


def tenant_get_or_404(model, request, **kwargs):
    """
    Equivalente ao get_object_or_404 mas sempre injeta filtro de empresa.
    Se o usuário não pertence a nenhuma empresa (superadmin), não filtra.

    Uso:
        obj = tenant_get_or_404(Transacao, request, pk=rid)
    """
    empresa = getattr(request, 'empresa', None)
    if empresa is not None:
        kwargs['empresa'] = empresa
    return _goo404(model, **kwargs)


def tenant_get_qs(model_or_qs, request):
    """
    Retorna queryset filtrado por empresa.
    Aceita Model.objects ou queryset já iniciado.
    """
    empresa = getattr(request, 'empresa', None)
    if hasattr(model_or_qs, 'all'):
        qs = model_or_qs.all()
    else:
        qs = model_or_qs
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    return qs
