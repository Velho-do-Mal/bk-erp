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
        "ativo": servico.ativo,
    }


def _item_material_to_dict(item: ItemMaterial) -> dict:
    return {
        "id": item.id,
        "material_id": item.material_id,
        "material": item.material.descricao,
        "unidade": item.material.unidade,
        "quantidade": float(item.quantidade or 0),
        "valor_unitario": float(item.valor_unitario or 0),
        "valor_total": float(item.valor_total or 0),
    }


def _item_servico_to_dict(item: ItemServico) -> dict:
    return {
        "id": item.id,
        "servico_id": item.servico_id,
        "servico": item.servico.nome,
        "unidade": item.servico.unidade,
        "quantidade": float(item.quantidade or 0),
        "valor_unitario": float(item.valor_unitario or 0),
        "valor_total": float(item.valor_total or 0),
    }


def _totais_orcamento(orcamento: Orcamento | None) -> dict:
    if not orcamento:
        return {"total_materiais": 0.0, "total_servicos": 0.0, "total_geral": 0.0}
    total_materiais = Decimal("0")
    total_servicos = Decimal("0")
    for item in orcamento.itens_material.select_related("material").all():
        total_materiais += item.valor_total or Decimal("0")
    for item in orcamento.itens_servico.select_related("servico").all():
        total_servicos += item.valor_total or Decimal("0")
    total_geral = total_materiais + total_servicos
    return {
        "total_materiais": float(total_materiais),
        "total_servicos": float(total_servicos),
        "total_geral": float(total_geral),
    }


@require_GET
def dashboard(request):
    obras = Obra.objects.select_related("cliente", "projeto").all()
    clientes = Cliente.objects.filter(ativo=True).order_by("nome")
    materiais = MaterialCadastro.objects.filter(ativo=True).order_by("descricao")
    servicos = ProdutoServico.objects.filter(ativo=True).order_by("nome")
    projetos = Projeto.objects.all().order_by("nome") if Projeto is not None else []

    orcamento_id = request.GET.get("orcamento_id")
    orcamento = None
    if orcamento_id:
        try:
            orcamento = Orcamento.objects.select_related(
                "obra", "obra__cliente", "obra__projeto"
            ).get(id=orcamento_id)
        except Orcamento.DoesNotExist:
            orcamento = None

    if not orcamento:
        orcamento = Orcamento.objects.select_related(
            "obra", "obra__cliente", "obra__projeto"
        ).order_by("-criado_em").first()

    itens_material = []
    itens_servico = []
    totais = _totais_orcamento(orcamento)

    if orcamento:
        itens_material = [
            _item_material_to_dict(item)
            for item in orcamento.itens_material.select_related("material").all()
        ]
        itens_servico = [
            _item_servico_to_dict(item)
            for item in orcamento.itens_servico.select_related("servico").all()
        ]

    context = {
        "obras": obras,
        "clientes": clientes,
        "materiais": materiais,
        "servicos": servicos,
        "projetos": projetos,
        "orcamento": orcamento,
        "itens_material": itens_material,
        "itens_servico": itens_servico,
        "totais": totais,
    }

    try:
        return render(request, "orcamento/dashboard.html", context)
    except TemplateDoesNotExist:
        payload = {
            "ok": True,
            "orcamento_id": orcamento.id if orcamento else None,
            "obra": orcamento.obra.nome if orcamento else None,
            "cliente": (orcamento.obra.cliente.nome if orcamento and orcamento.obra and orcamento.obra.cliente else None),
            "projeto": (orcamento.obra.projeto.nome if orcamento and orcamento.obra and orcamento.obra.projeto else None),
            "itens_material": itens_material,
            "itens_servico": itens_servico,
            "totais": totais,
        }
        return JsonResponse(payload, encoder=DjangoJSONEncoder)


@require_http_methods(["GET", "POST"])
def listar_materiais(request):
    termo = request.GET.get("q") or request.POST.get("q") or ""
    queryset = MaterialCadastro.objects.filter(ativo=True)
    if termo:
        queryset = queryset.filter(
            Q(descricao__icontains=termo)
            | Q(codigo_cliente__icontains=termo)
            | Q(codigo_bk__icontains=termo)
        )
    materiais = [_material_to_dict(m) for m in queryset.order_by("descricao")[:50]]
    return JsonResponse({"ok": True, "resultados": materiais})


@require_http_methods(["POST"])
def salvar_material(request):
    data = _request_data(request)
    descricao = (data.get("descricao") or "").strip()
    if not descricao:
        return JsonResponse({"ok": False, "erro": "Descrição é obrigatória."}, status=400)

    material_id = data.get("id")
    codigo_cliente = (data.get("codigo_cliente") or "").strip()
    codigo_bk = (data.get("codigo_bk") or "").strip()
    unidade = (data.get("unidade") or "un").strip() or "un"
    valor_unitario = _to_decimal(data.get("valor_unitario"), default="0")
    ativo = str(data.get("ativo", "true")).lower() in ("1", "true", "sim", "on")

    try:
        if material_id:
            material = get_object_or_404(MaterialCadastro, id=material_id)
            mensagem = "Material atualizado com sucesso."
        else:
            material = MaterialCadastro()
            mensagem = "Material criado com sucesso."

        material.codigo_cliente = codigo_cliente
        material.codigo_bk = codigo_bk
        material.descricao = descricao
        material.unidade = unidade
        material.valor_unitario = valor_unitario
        material.ativo = ativo
        material.save()
        return JsonResponse({"ok": True, "mensagem": mensagem, "material": _material_to_dict(material)})
    except Exception as exc:
        return JsonResponse({"ok": False, "erro": f"Erro ao salvar material: {exc}"}, status=500)


@require_http_methods(["POST"])
def salvar_obra(request):
    data = _request_data(request)

    cliente_id = data.get("cliente_id")
    cliente = get_object_or_404(Cliente, id=cliente_id) if cliente_id else None

    # CORRECAO 1: buscar e salvar o Projeto vinculado
    projeto = None
    projeto_id = data.get("projeto_id")
    if projeto_id and Projeto is not None:
        try:
            projeto = Projeto.objects.get(id=projeto_id)
        except Projeto.DoesNotExist:
            projeto = None

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
    orcamento, _ = Orcamento.objects.get_or_create(obra=obra, defaults={"nome": nome_orcamento})
    if orcamento.nome != nome_orcamento:
        orcamento.nome = nome_orcamento
        orcamento.save(update_fields=["nome"])

    return JsonResponse({
        "ok": True,
        "mensagem": "Obra criada com sucesso." if criada else "Obra atualizada com sucesso.",
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


@require_http_methods(["POST"])
def salvar_item_material(request):
    data = _request_data(request)
    orcamento_id = data.get("orcamento_id")
    material_id = data.get("material_id")

    if not orcamento_id:
        return JsonResponse({"ok": False, "erro": "orcamento_id é obrigatório."}, status=400)
    if not material_id:
        return JsonResponse({"ok": False, "erro": "material_id é obrigatório."}, status=400)

    orcamento = get_object_or_404(Orcamento, id=orcamento_id)
    material = get_object_or_404(MaterialCadastro, id=material_id)
    quantidade = _to_decimal(data.get("quantidade"), default="1")
    valor_unitario = _to_decimal(data.get("valor_unitario"), default=str(material.valor_unitario or 0))

    item = ItemMaterial.objects.create(
        orcamento=orcamento,
        material=material,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
    )
    return JsonResponse({"ok": True, "mensagem": "Item adicionado.", "item": _item_material_to_dict(item), "totais": _totais_orcamento(orcamento)})


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


@require_GET
def autocomplete_servico(request):
    termo = (request.GET.get("q") or "").strip()
    queryset = ProdutoServico.objects.filter(ativo=True)
    if termo:
        queryset = queryset.filter(
            Q(nome__icontains=termo) | Q(codigo__icontains=termo) | Q(descricao__icontains=termo)
        )
    resultados = [_servico_to_dict(s) for s in queryset.order_by("nome")[:20]]
    return JsonResponse({"ok": True, "resultados": resultados})


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
    return JsonResponse({"ok": True, "mensagem": "Item adicionado.", "item": _item_servico_to_dict(item), "totais": _totais_orcamento(orcamento)})


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


@require_GET
def exportar_excel(request, orcamento_id):
    orcamento = get_object_or_404(
        Orcamento.objects.select_related("obra", "obra__cliente", "obra__projeto"),
        id=orcamento_id
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

    writer.writerow(["MATERIAIS"])
    writer.writerow(["Descrição", "Unidade", "Quantidade", "Valor Unitário", "Valor Total"])
    for item in orcamento.itens_material.select_related("material").all():
        writer.writerow([item.material.descricao, item.material.unidade, item.quantidade, item.valor_unitario, item.valor_total])

    writer.writerow([])
    writer.writerow(["SERVIÇOS"])
    writer.writerow(["Nome", "Unidade", "Quantidade", "Valor Unitário", "Valor Total"])
    for item in orcamento.itens_servico.select_related("servico").all():
        writer.writerow([item.servico.nome, item.servico.unidade, item.quantidade, item.valor_unitario, item.valor_total])

    totais = _totais_orcamento(orcamento)
    writer.writerow([])
    writer.writerow(["Total Materiais", totais["total_materiais"]])
    writer.writerow(["Total Serviços", totais["total_servicos"]])
    writer.writerow(["Total Geral", totais["total_geral"]])
    return response
