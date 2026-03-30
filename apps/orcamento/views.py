from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template import TemplateDoesNotExist
from django.views.decorators.http import require_GET, require_http_methods

from apps.cadastros.models import Cliente
from apps.servicos.models import ProdutoServico
from .models import MaterialCadastro, Obra, Orcamento, ItemMaterial, ItemServico

try:
    from apps.projetos.models import Projeto
except Exception:
    Projeto = None


def _to_decimal(value, default="0"):
    if value in (None, "", []):
        value = default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        text = str(value).strip().replace(".", "").replace(",", ".")
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(str(default))


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _request_data(request):
    if request.content_type and "application/json" in request.content_type:
        data = _json_body(request)
        return data if isinstance(data, dict) else {}
    if request.method == "GET":
        return request.GET.dict()
    return request.POST.dict()


def _material_to_dict(material: MaterialCadastro) -> dict:
    return {
        "id": material.id,
        "codigo_cliente": material.codigo_cliente,
        "codigo_bk": material.codigo_bk,
        "descricao": material.descricao,
        "unidade": material.unidade,
        "valor_unitario": float(material.valor_unitario or 0),
        "ativo": material.ativo,
    }


def _servico_to_dict(servico: ProdutoServico) -> dict:
    return {
        "id": servico.id,
        "codigo": servico.codigo,
        "nome": servico.nome,
        "descricao": servico.descricao,
        "unidade": servico.unidade,
        "preco_unitario": float(servico.preco_unitario or 0),
        "tipo": servico.tipo,
        "ativo": servico.ativ
