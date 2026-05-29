from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required   # ← adicionado
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.cadastros.models import Cliente
from apps.servicos.models import ProdutoServico
from .models import Obra, Orcamento, ItemMaterial, ItemServico

def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, 'empresa', None)



try:
    from apps.projetos.models import Projeto
except Exception:
    Projeto = None


# ─── helpers ────────────────────────────────────────────────────────────────

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


def _produto_to_dict(p: ProdutoServico) -> dict:
    return {
        "id": p.id,
        "codigo": p.codigo,
        "nome": p.nome,
        "descricao": p.descricao,
        "unidade": p.unidade,
        "preco_unitario": float(p.preco_unitario or 0),
        "tipo": p.tipo,
        "ativo": p.ativo,
    }


def _item_material_to_dict(item: ItemMaterial) -> dict:
    return {
        "id": item.id,
        "produto_id": item.produto_id,
        "produto": item.produto.nome,
        "codigo": item.produto.codigo,
        "unidade": item.produto.unidade,
        "quantidade": float(item.quantidade or 0),
        "valor_unitario": float(item.valor_unitario or 0),
        "valor_total": float(item.valor_total or 0),
    }


def _item_servico_to_dict(item: ItemServico) -> dict:
    return {
        "id": item.id,
        "servico_id": item.servico_id,
        "servico": item.servico.nome,
        "codigo": item.servico.codigo,
        "unidade": item.servico.unidade,
        "quantidade": float(item.quantidade or 0),
        "valor_unitario": float(item.valor_unitario or 0),
        "valor_total": float(item.valor_total or 0),
    }


def _totais_orcamento(orcamento: Orcamento | None) -> dict:
    if not orcamento:
        return {"total_materiais": 0.0, "total_servicos": 0.0, "total_geral": 0.0}
    total_materiais = sum(
        i.valor_total or Decimal("0")
        for i in orcamento.itens_material.select_related("produto").all()
    )
    total_servicos = sum(
        i.valor_total or Decimal("0")
        for i in orcamento.itens_servico.select_related("servico").all()
    )
    total_geral = total_materiais + total_servicos
    return {
        "total_materiais": float(total_materiais),
        "total_servicos": float(total_servicos),
        "total_geral": float(total_geral),
    }


# ─── views ──────────────────────────────────────────────────────────────────

@login_required
@require_GET
def dashboard(request):
    obras = Obra.objects.select_related("cliente", "projeto").all()
    clientes = Cliente.objects.filter(empresa=_empresa(request), ativo=True).order_by("nome")
    projetos = Projeto.objects.filter(empresa=_empresa(request)).order_by("nome") if Projeto is not None else []

    produtos_qs = ProdutoServico.objects.filter(empresa=_empresa(request), tipo__in=["produto", "ambos"]).order_by("nome")
    servicos_qs = ProdutoServico.objects.filter(empresa=_empresa(request), tipo__in=["servico", "ambos"]).order_by("nome")

    def _qs_to_list(qs):
        return [
            {
                "id": obj.id,
                "nome": obj.nome or "",
                "codigo": obj.codigo or "",
                "unidade": obj.unidade or "un",
                "preco": float(obj.preco_unitario or 0),
            }
            for obj in qs
        ]

    produtos = produtos_qs
    servicos = servicos_qs
    produtos_list = _qs_to_list(produtos_qs)
    servicos_list = _qs_to_list(servicos_qs)

    orcamento_id = request.GET.get("orcamento_id")
    orcamento = None

    if orcamento_id:
        try:
            orcamento = Orcamento.objects.select_related(
                "obra", "obra__cliente", "obra__projeto"
            ).get(id=orcamento_id)
        except Orcamento.DoesNotExist:
            pass

    if not orcamento:
        orcamento = Orcamento.objects.select_related(
            "obra", "obra__cliente", "obra__projeto"
        ).order_by("-criado_em").first()

    itens_material = []
    itens_servico = []
    totais = _totais_orcamento(orcamento)

    if orcamento:
        itens_material = [
            _item_material_to_dict(i)
            for i in orcamento.itens_material.select_related("produto").all()
        ]
        itens_servico = [
            _item_servico_to_dict(i)
            for i in orcamento.itens_servico.select_related("servico").all()
        ]

    context = {
        "obras": obras,
        "clientes": clientes,
        "projetos": projetos,
        "produtos": produtos,
        "servicos": servicos,
        "produtos_list": produtos_list,
        "servicos_list": servicos_list,
        "orcamento": orcamento,
        "itens_material": itens_material,
        "itens_servico": itens_servico,
        "totais": totais,
    }

    return render(request, "orcamento/orcamento.html", context)


@login_required
@require_http_methods(["POST"])
def salvar_obra(request):
    data = _request_data(request)
    cliente_id = data.get("cliente_id")
    cliente = get_object_or_404(Cliente, id=cliente_id) if cliente_id else None

    projeto = None
    projeto_id = data.get("projeto_id")
    if projeto_id and Projeto is not None:
        try:
            projeto = Projeto.objects.get(id=projeto_id)
        except Projeto.DoesNotExist:
            pass

    nome = (data.get("nome") or (projeto.nome if projeto else "") or "").strip()

    if not nome:
        return JsonResponse({"ok": False, "erro": "Nome da obra é obrigatório."}, status=400)

    obra_id = data.get("id")

    if obra_id:
        obra = get_object_or_404(Obra, id=obra_id)
        obra.nome = nome
        obra.cliente = cliente
        obra.projeto = projeto
        obra.save()
        criada = False
    else:
        obra = Obra.objects.create(nome=nome, cliente=cliente, projeto=projeto)
        criada = True

    nome_orcamento = (data.get("nome_orcamento") or "Orçamento").strip() or "Orçamento"

    # ← CORRIGIDO: get_or_create pode lançar MultipleObjectsReturned se houver
    #   mais de um orçamento para a mesma obra. Usa filter().first() no lugar.
    orcamento = Orcamento.objects.filter(empresa=_empresa(request), obra=obra).order_by("-criado_em").first()
    if not orcamento:
        orcamento = Orcamento.objects.create(obra=obra, nome=nome_orcamento)
    elif orcamento.nome != nome_orcamento:
        orcamento.nome = nome_orcamento
        orcamento.save(update_fields=["nome"])

    return JsonResponse({
        "ok": True,
        "mensagem": "Obra criada." if criada else "Obra atualizada.",
        "obra": {
            "id": obra.id,
            "nome": obra.nome,
            "cliente_id": obra.cliente_id,
            "cliente": obra.cliente.nome if obra.cliente else None,
            "projeto_id": obra.projeto_id,
            "projeto": obra.projeto.nome if obra.projeto else None,
        },
        "orcamento": {"id": orcamento.id, "nome": orcamento.nome},
    })


@login_required
@require_http_methods(["GET", "POST"])
def autocomplete_produto(request):
    """Autocomplete para produtos/materiais (tipo produto ou ambos)."""
    termo = (request.GET.get("q") or request.POST.get("q") or "").strip()
    qs = ProdutoServico.objects.filter(empresa=_empresa(request), ativo=True, tipo__in=["produto", "ambos"])

    if termo:
        qs = qs.filter(Q(nome__icontains=termo) | Q(codigo__icontains=termo))

    return JsonResponse({"ok": True, "resultados": [_produto_to_dict(p) for p in qs.order_by("nome")[:50]]})


@login_required
@require_http_methods(["GET", "POST"])
def autocomplete_servico(request):
    """Autocomplete para serviços (tipo servico ou ambos)."""
    termo = (request.GET.get("q") or request.POST.get("q") or "").strip()
    qs = ProdutoServico.objects.filter(empresa=_empresa(request), ativo=True, tipo__in=["servico", "ambos"])

    if termo:
        qs = qs.filter(Q(nome__icontains=termo) | Q(codigo__icontains=termo))

    return JsonResponse({"ok": True, "resultados": [_produto_to_dict(p) for p in qs.order_by("nome")[:50]]})


@login_required
@require_http_methods(["POST"])
def salvar_item_material(request):
    data = _request_data(request)
    orcamento_id = data.get("orcamento_id")
    produto_id = data.get("produto_id")

    if not orcamento_id:
        return JsonResponse({"ok": False, "erro": "orcamento_id é obrigatório."}, status=400)
    if not produto_id:
        return JsonResponse({"ok": False, "erro": "produto_id é obrigatório."}, status=400)

    orcamento = get_object_or_404(Orcamento, id=orcamento_id)
    produto = get_object_or_404(ProdutoServico, id=produto_id)

    quantidade = _to_decimal(data.get("quantidade"), default="1")
    valor_unitario = _to_decimal(data.get("valor_unitario"), default=str(produto.preco_unitario or 0))

    item = ItemMaterial.objects.create(
        orcamento=orcamento,
        produto=produto,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
    )

    return JsonResponse({
        "ok": True,
        "mensagem": "Material adicionado.",
        "item": _item_material_to_dict(item),
        "totais": _totais_orcamento(orcamento),
    })


@login_required
@require_http_methods(["POST"])
def excluir_item_material(request):
    data = _request_data(request)
    item_id = data.get("id") or data.get("item_id")

    if not item_id:
        return JsonResponse({"ok": False, "erro": "id do item é obrigatório."}, status=400)

    item = get_object_or_404(ItemMaterial, id=item_id)
    orcamento = item.orcamento
    item.delete()

    return JsonResponse({"ok": True, "mensagem": "Item excluído.", "totais": _totais_orcamento(orcamento)})


@login_required
@require_http_methods(["POST"])
def salvar_item_servico(request):
    data = _request_data(request)
    orcamento_id = data.get("orcamento_id")
    servico_id = data.get("servico_id")

    if not orcamento_id:
        return JsonResponse({"ok": False, "erro": "orcamento_id é obrigatório."}, status=400)
    if not servico_id:
        return JsonResponse({"ok": False, "erro": "servico_id é obrigatório."}, status=400)

    orcamento = get_object_or_404(Orcamento, id=orcamento_id)
    servico = get_object_or_404(ProdutoServico, id=servico_id)

    quantidade = _to_decimal(data.get("quantidade"), default="1")
    valor_unitario = _to_decimal(data.get("valor_unitario"), default=str(servico.preco_unitario or 0))

    item = ItemServico.objects.create(
        orcamento=orcamento,
        servico=servico,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
    )

    return JsonResponse({
        "ok": True,
        "mensagem": "Serviço adicionado.",
        "item": _item_servico_to_dict(item),
        "totais": _totais_orcamento(orcamento),
    })


@login_required
@require_http_methods(["POST"])
def excluir_item_servico(request):
    data = _request_data(request)
    item_id = data.get("id") or data.get("item_id")

    if not item_id:
        return JsonResponse({"ok": False, "erro": "id do item é obrigatório."}, status=400)

    item = get_object_or_404(ItemServico, id=item_id)
    orcamento = item.orcamento
    item.delete()

    return JsonResponse({"ok": True, "mensagem": "Item excluído.", "totais": _totais_orcamento(orcamento)})


@login_required
@require_GET
def exportar_excel(request, orcamento_id):
    orcamento = get_object_or_404(
        Orcamento.objects.select_related("obra", "obra__cliente", "obra__projeto"),
        id=orcamento_id,
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="orcamento_{orcamento.id}.csv"'
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")

    writer.writerow(["Orçamento", orcamento.nome])
    writer.writerow(["Obra", orcamento.obra.nome])
    writer.writerow(["Cliente", orcamento.obra.cliente.nome if orcamento.obra.cliente else ""])
    writer.writerow(["Projeto", orcamento.obra.projeto.nome if orcamento.obra.projeto else ""])
    writer.writerow([])

    from collections import OrderedDict

    mapa_mat = OrderedDict()
    for item in orcamento.itens_material.select_related("produto").all():
        key = item.produto_id
        if key in mapa_mat:
            mapa_mat[key]["quantidade"] += item.quantidade
            mapa_mat[key]["valor_total"] += item.valor_total
        else:
            mapa_mat[key] = {
                "codigo": item.produto.codigo,
                "nome": item.produto.nome,
                "unidade": item.produto.unidade,
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
                "valor_total": item.valor_total,
            }

    writer.writerow(["MATERIAIS/PRODUTOS"])
    writer.writerow(["Código", "Descrição", "Unidade", "Quantidade", "Valor Unitário", "Valor Total"])
    for m in mapa_mat.values():
        writer.writerow([m["codigo"], m["nome"], m["unidade"], m["quantidade"], m["valor_unitario"], m["valor_total"]])

    mapa_svc = OrderedDict()
    for item in orcamento.itens_servico.select_related("servico").all():
        key = item.servico_id
        if key in mapa_svc:
            mapa_svc[key]["quantidade"] += item.quantidade
            mapa_svc[key]["valor_total"] += item.valor_total
        else:
            mapa_svc[key] = {
                "codigo": item.servico.codigo,
                "nome": item.servico.nome,
                "unidade": item.servico.unidade,
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
                "valor_total": item.valor_total,
            }

    writer.writerow([])
    writer.writerow(["SERVIÇOS"])
    writer.writerow(["Código", "Nome", "Unidade", "Quantidade", "Valor Unitário", "Valor Total"])
    for s in mapa_svc.values():
        writer.writerow([s["codigo"], s["nome"], s["unidade"], s["quantidade"], s["valor_unitario"], s["valor_total"]])

    totais = _totais_orcamento(orcamento)
    writer.writerow([])
    writer.writerow(["Total Materiais", totais["total_materiais"]])
    writer.writerow(["Total Serviços", totais["total_servicos"]])
    writer.writerow(["Total Geral", totais["total_geral"]])

    return response
