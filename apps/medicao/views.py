from __future__ import annotations

import base64
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.cadastros.models import Cliente
from apps.core.tenant import tenant_get_or_404
from apps.servicos.models import ProdutoServico

from .models import BoletimMedicao, ItemContrato, MedicaoItem, PeriodoMedicao

try:
    from apps.projetos.models import Projeto
except Exception:
    Projeto = None


def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, "empresa", None)


def _qs_empresa(qs, request):
    """
    Aplica filtro multiempresa de forma segura.

    - Se o model tem campo empresa: empresa=empresa
    - Se o model tem campo projeto: projeto__empresa=empresa
    - Se o model tem campo boletim: boletim__empresa=empresa
    - Se o model tem campo periodo: periodo__boletim__empresa=empresa
    - Se o model tem campo item: item__boletim__empresa=empresa

    Isso evita erro em models filhos do Boletim de Medição que não têm
    o campo empresa diretamente.
    """
    empresa = _empresa(request)

    if empresa is None:
        return qs

    model = qs.model
    field_names = {f.name for f in model._meta.get_fields()}

    if "empresa" in field_names:
        return qs.filter(empresa=empresa)

    if "projeto" in field_names:
        return qs.filter(projeto__empresa=empresa)

    if "boletim" in field_names:
        return qs.filter(boletim__empresa=empresa)

    if "periodo" in field_names:
        return qs.filter(periodo__boletim__empresa=empresa)

    if "item" in field_names:
        return qs.filter(item__boletim__empresa=empresa)

    return qs


# ─── Helpers ────────────────────────────────────────────────────────────────

def _to_decimal(value, default="0"):
    if value in (None, "", []):
        value = default

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    try:
        text = str(value).strip()

        # Trata padrão brasileiro: 1.234,56 -> 1234.56
        if "," in text:
            text = text.replace(".", "").replace(",", ".")

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


def _req_data(request):
    if request.content_type and "application/json" in request.content_type:
        data = _json_body(request)
        return data if isinstance(data, dict) else {}

    if request.method == "GET":
        return request.GET.dict()

    return request.POST.dict()


def _bm_to_dict(bm: BoletimMedicao) -> dict:
    return {
        "id": bm.id,
        "nome": bm.nome,
        "cliente_id": bm.cliente_id,
        "cliente": bm.cliente.nome if bm.cliente else "",
        "projeto_id": bm.projeto_id,
        "projeto": bm.projeto.nome if bm.projeto else "",
        "contrato": bm.contrato,
        "codigo_obra": bm.codigo_obra,
        "total_contrato": float(bm.total_contrato),
        "num_periodos": bm.periodos.count(),
        "proximo_bm": bm.proximo_numero_bm,
    }


def _item_to_dict(item: ItemContrato) -> dict:
    return {
        "id": item.id,
        "servico_id": item.servico_id,
        "codigo": item.codigo,
        "descricao": item.descricao,
        "quantidade_total": float(item.quantidade_total or 0),
        "unidade": item.unidade,
        "preco_unitario": float(item.preco_unitario or 0),
        "preco_total": float(item.preco_total or 0),
        "ordem": item.ordem,
    }


def _periodo_to_dict(p: PeriodoMedicao) -> dict:
    return {
        "id": p.id,
        "numero": p.numero,
        "label": p.label,
        "data_inicio": p.data_inicio.strftime("%Y-%m-%d") if p.data_inicio else "",
        "data_fim": p.data_fim.strftime("%Y-%m-%d") if p.data_fim else "",
        "valor_total": float(p.valor_total_periodo),
    }


def _calcular_acumulados(boletim: BoletimMedicao, ate_periodo_id: int | None = None) -> dict:
    """Retorna {item_id: quantidade_acumulada} para todos os períodos até ate_periodo_id."""
    periodos_qs = boletim.periodos.all()

    if ate_periodo_id:
        try:
            p_ref = PeriodoMedicao.objects.get(id=ate_periodo_id, boletim=boletim)
            periodos_qs = periodos_qs.filter(numero__lte=p_ref.numero)
        except PeriodoMedicao.DoesNotExist:
            pass

    acum: dict[int, Decimal] = {}

    for p in periodos_qs:
        for m in p.medicoes.select_related("item").all():
            acum[m.item_id] = acum.get(m.item_id, Decimal("0")) + (m.quantidade_medida or Decimal("0"))

    return acum


def _montar_linhas(itens, medicoes_dict, acum_dict):
    """Monta lista de linhas para a grade de medição."""
    linhas = []

    for item in itens:
        qtd_medida = Decimal(str(medicoes_dict.get(item.id, 0)))
        qtd_acum = acum_dict.get(item.id, Decimal("0"))
        qtd_total = item.quantidade_total or Decimal("0")
        pu = item.preco_unitario or Decimal("0")

        valor_total_item = item.preco_total
        valor_medido_periodo = qtd_medida * pu
        valor_acum = qtd_acum * pu
        saldo = valor_total_item - valor_acum
        pct = (qtd_acum / qtd_total * 100) if qtd_total else Decimal("0")

        linhas.append({
            "item": item,
            "qtd_medida": float(qtd_medida),
            "qtd_acum": float(qtd_acum),
            "valor_total_item": float(valor_total_item),
            "valor_medido_periodo": float(valor_medido_periodo),
            "valor_acum": float(valor_acum),
            "saldo": float(saldo),
            "pct": round(float(pct), 2),
        })

    return linhas


def _logo_to_b64(field_file):
    """
    Converte FileField para base64 sem derrubar a página caso o arquivo não exista
    no storage/S3/Railway Volume.
    """
    if not field_file:
        return ""

    try:
        with field_file.open("rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ─── Views principais ───────────────────────────────────────────────────────

@login_required
@require_GET
def dashboard(request):
    """Lista todos os Boletins de Medição."""
    boletins = _qs_empresa(BoletimMedicao.objects, request).select_related("cliente", "projeto")

    clientes = _qs_empresa(Cliente.objects, request).filter(ativo=True).order_by("nome")

    if Projeto is not None:
        projetos = _qs_empresa(Projeto.objects, request).order_by("nome")
    else:
        projetos = []

    return render(request, "medicao/dashboard.html", {
        "boletins": boletins,
        "clientes": clientes,
        "projetos": projetos,
    })


@login_required
def detalhe(request, bm_id):
    """Página principal do BM com as abas."""
    boletim = get_object_or_404(
        _qs_empresa(BoletimMedicao.objects, request).select_related("cliente", "projeto"),
        id=bm_id,
    )

    clientes = _qs_empresa(Cliente.objects, request).filter(ativo=True).order_by("nome")

    if Projeto is not None:
        projetos = _qs_empresa(Projeto.objects, request).order_by("nome")
    else:
        projetos = []

    servicos = _qs_empresa(ProdutoServico.objects, request).filter(ativo=True).order_by("nome")

    itens = list(boletim.itens.select_related("servico").order_by("ordem", "id"))
    periodos = list(boletim.periodos.order_by("numero"))

    periodo_id = request.GET.get("periodo_id")
    periodo_ativo = None

    if periodo_id:
        try:
            periodo_ativo = PeriodoMedicao.objects.get(id=periodo_id, boletim=boletim)
        except PeriodoMedicao.DoesNotExist:
            pass

    if not periodo_ativo and periodos:
        periodo_ativo = periodos[-1]

    medicoes_dict: dict[int, Decimal] = {}

    if periodo_ativo:
        for m in periodo_ativo.medicoes.all():
            medicoes_dict[m.item_id] = m.quantidade_medida or Decimal("0")

    acum_ate = _calcular_acumulados(boletim, ate_periodo_id=periodo_ativo.id if periodo_ativo else None)
    linhas = _montar_linhas(itens, medicoes_dict, acum_ate)

    total_contrato = float(boletim.total_contrato)
    total_periodo = sum(l["valor_medido_periodo"] for l in linhas)
    total_acum = sum(l["valor_acum"] for l in linhas)
    total_saldo = total_contrato - total_acum
    pct_total = round((total_acum / total_contrato * 100) if total_contrato else 0, 2)

    logo_bk_b64 = _logo_to_b64(boletim.logo_bk)
    logo_cliente_b64 = _logo_to_b64(boletim.logo_cliente)

    return render(request, "medicao/detalhe.html", {
        "boletim": boletim,
        "clientes": clientes,
        "projetos": projetos,
        "servicos": servicos,
        "itens": itens,
        "periodos": periodos,
        "periodo_ativo": periodo_ativo,
        "linhas": linhas,
        "total_contrato": total_contrato,
        "total_periodo": total_periodo,
        "total_acum": total_acum,
        "total_saldo": total_saldo,
        "pct_total": pct_total,
        "logo_bk_b64": logo_bk_b64,
        "logo_bk_tipo": boletim.logo_bk_tipo,
        "logo_cliente_b64": logo_cliente_b64,
        "logo_cliente_tipo": boletim.logo_cliente_tipo,
    })


@login_required
@require_GET
def print_periodo(request, bm_id, periodo_id):
    """Página de impressão do período."""
    boletim = get_object_or_404(
        _qs_empresa(BoletimMedicao.objects, request).select_related("cliente", "projeto"),
        id=bm_id,
    )
    periodo = get_object_or_404(PeriodoMedicao, id=periodo_id, boletim=boletim)

    itens = list(boletim.itens.select_related("servico").order_by("ordem", "id"))
    medicoes_dict = {m.item_id: m.quantidade_medida or Decimal("0") for m in periodo.medicoes.all()}
    acum_ate = _calcular_acumulados(boletim, ate_periodo_id=periodo.id)
    linhas = _montar_linhas(itens, medicoes_dict, acum_ate)

    total_contrato = float(boletim.total_contrato)
    total_periodo = sum(l["valor_medido_periodo"] for l in linhas)
    total_acum = sum(l["valor_acum"] for l in linhas)

    logo_bk_b64 = _logo_to_b64(boletim.logo_bk)
    logo_cliente_b64 = _logo_to_b64(boletim.logo_cliente)

    return render(request, "medicao/print_periodo.html", {
        "boletim": boletim,
        "periodo": periodo,
        "linhas": linhas,
        "total_contrato": total_contrato,
        "total_periodo": total_periodo,
        "total_acum": total_acum,
        "logo_bk_b64": logo_bk_b64,
        "logo_bk_tipo": boletim.logo_bk_tipo,
        "logo_cliente_b64": logo_cliente_b64,
        "logo_cliente_tipo": boletim.logo_cliente_tipo,
    })


@login_required
@require_GET
def print_consolidado(request, bm_id):
    """Página de impressão consolidada."""
    boletim = get_object_or_404(
        _qs_empresa(BoletimMedicao.objects, request).select_related("cliente", "projeto"),
        id=bm_id,
    )

    itens = list(boletim.itens.select_related("servico").order_by("ordem", "id"))
    periodos = list(boletim.periodos.order_by("numero"))

    qtd_map: dict[int, dict[int, float]] = {item.id: {} for item in itens}

    for p in periodos:
        for m in p.medicoes.all():
            qtd_map.setdefault(m.item_id, {})[p.numero] = float(m.quantidade_medida or 0)

    linhas = []

    for item in itens:
        qtds = [qtd_map[item.id].get(p.numero, 0.0) for p in periodos]
        qtd_acum = sum(qtds)
        pu = float(item.preco_unitario or 0)
        valor_acum = round(qtd_acum * pu, 2)
        valor_total = float(item.preco_total)
        saldo = round(valor_total - valor_acum, 2)
        pct = round((qtd_acum / float(item.quantidade_total) * 100) if item.quantidade_total else 0, 2)

        linhas.append({
            "item": item,
            "qtds_por_periodo": qtds,
            "qtd_acum": round(qtd_acum, 3),
            "valor_acum": valor_acum,
            "valor_total": round(valor_total, 2),
            "saldo": saldo,
            "pct": pct,
        })

    logo_bk_b64 = _logo_to_b64(boletim.logo_bk)
    logo_cliente_b64 = _logo_to_b64(boletim.logo_cliente)

    return render(request, "medicao/print_consolidado.html", {
        "boletim": boletim,
        "periodos": periodos,
        "linhas": linhas,
        "logo_bk_b64": logo_bk_b64,
        "logo_bk_tipo": boletim.logo_bk_tipo,
        "logo_cliente_b64": logo_cliente_b64,
        "logo_cliente_tipo": boletim.logo_cliente_tipo,
    })


# ─── APIs JSON ───────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_salvar_boletim(request):
    """Cria ou atualiza um BoletimMedicao."""
    data = _req_data(request)
    bm_id = data.get("id")

    cliente_id = data.get("cliente_id")
    cliente = None

    if cliente_id:
        cliente = get_object_or_404(_qs_empresa(Cliente.objects, request), id=cliente_id)

    projeto = None
    projeto_id = data.get("projeto_id")

    if projeto_id and Projeto is not None:
        try:
            projeto = _qs_empresa(Projeto.objects, request).get(id=projeto_id)
        except Projeto.DoesNotExist:
            projeto = None

    nome = (data.get("nome") or (projeto.nome if projeto else "") or "").strip()

    if not nome:
        return JsonResponse({"ok": False, "erro": "Nome é obrigatório."}, status=400)

    if bm_id:
        bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
        criada = False
    else:
        bm = BoletimMedicao()
        criada = True

    bm.empresa = _empresa(request)
    bm.nome = nome
    bm.cliente = cliente
    bm.projeto = projeto
    bm.contrato = (data.get("contrato") or "").strip()
    bm.codigo_obra = (data.get("codigo_obra") or "").strip()

    for campo_b64, campo_tipo, campo_nome, campo_file in [
        ("logo_bk_b64", "logo_bk_tipo", "logo_bk_nome", "logo_bk"),
        ("logo_cliente_b64", "logo_cliente_tipo", "logo_cliente_nome", "logo_cliente"),
    ]:
        raw = data.get(campo_b64) or ""

        if raw:
            try:
                from django.core.files.base import ContentFile

                # Aceita data URI: data:image/png;base64,xxxxx
                if "," in raw and raw.strip().lower().startswith("data:"):
                    raw = raw.split(",", 1)[1]

                file_bytes = base64.b64decode(raw)
                nome_arquivo = data.get(campo_nome) or f"{campo_file}.bin"

                getattr(bm, campo_file).save(nome_arquivo, ContentFile(file_bytes), save=False)
                setattr(bm, campo_tipo, data.get(campo_tipo) or "")
                setattr(bm, campo_nome, data.get(campo_nome) or "")
            except Exception:
                pass

    bm.save()

    return JsonResponse({
        "ok": True,
        "mensagem": "Boletim criado." if criada else "Boletim atualizado.",
        "bm": _bm_to_dict(bm),
        "redirect": f"/medicao/{bm.id}/",
    })


@login_required
@require_POST
def api_excluir_boletim(request):
    data = _req_data(request)
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=data.get("id"))
    bm.delete()
    return JsonResponse({"ok": True, "mensagem": "Boletim excluído."})


@login_required
@require_POST
def api_salvar_item(request, bm_id):
    """Cria ou atualiza um ItemContrato no boletim."""
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    data = _req_data(request)
    item_id = data.get("id")

    servico = None
    servico_id = data.get("servico_id")

    if servico_id:
        try:
            servico = _qs_empresa(ProdutoServico.objects, request).get(id=servico_id)
        except ProdutoServico.DoesNotExist:
            servico = None

    descricao = (data.get("descricao") or (servico.nome if servico else "")).strip()

    if not descricao:
        return JsonResponse({"ok": False, "erro": "Descrição é obrigatória."}, status=400)

    if item_id:
        item = get_object_or_404(ItemContrato, id=item_id, boletim=bm)
    else:
        item = ItemContrato(boletim=bm)

    item.servico = servico
    item.codigo = (data.get("codigo") or (servico.codigo if servico else "") or "").strip()
    item.descricao = descricao
    item.unidade = (data.get("unidade") or (servico.unidade if servico else "un") or "un").strip()
    item.quantidade_total = _to_decimal(data.get("quantidade_total"), default="1")
    item.preco_unitario = _to_decimal(
        data.get("preco_unitario"),
        default=str(servico.preco_unitario) if servico else "0",
    )
    item.ordem = int(data.get("ordem") or 0)
    item.save()

    return JsonResponse({
        "ok": True,
        "mensagem": "Item salvo.",
        "item": _item_to_dict(item),
        "total_contrato": float(bm.total_contrato),
    })


@login_required
@require_POST
def api_excluir_item(request, bm_id):
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    data = _req_data(request)
    item = get_object_or_404(ItemContrato, id=data.get("id"), boletim=bm)
    item.delete()
    return JsonResponse({
        "ok": True,
        "mensagem": "Item excluído.",
        "total_contrato": float(bm.total_contrato),
    })


@login_required
@require_POST
def api_criar_periodo(request, bm_id):
    """Cria um novo período de medição BM-N."""
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    data = _req_data(request)

    numero = bm.proximo_numero_bm
    data_inicio = data.get("data_inicio")
    data_fim = data.get("data_fim")

    if not data_inicio or not data_fim:
        return JsonResponse({"ok": False, "erro": "Datas de início e fim são obrigatórias."}, status=400)

    periodo = PeriodoMedicao.objects.create(
        boletim=bm,
        numero=numero,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    for item in bm.itens.all():
        MedicaoItem.objects.get_or_create(
            periodo=periodo,
            item=item,
            defaults={"quantidade_medida": Decimal("0")},
        )

    return JsonResponse({
        "ok": True,
        "mensagem": f"{periodo.label} criado.",
        "periodo": _periodo_to_dict(periodo),
        "redirect": f"/medicao/{bm.id}/?periodo_id={periodo.id}",
    })


@login_required
@require_POST
def api_excluir_periodo(request, bm_id):
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    data = _req_data(request)
    periodo = get_object_or_404(PeriodoMedicao, id=data.get("periodo_id"), boletim=bm)
    periodo.delete()

    for i, p in enumerate(bm.periodos.order_by("numero"), start=1):
        if p.numero != i:
            p.numero = i
            p.save(update_fields=["numero"])

    return JsonResponse({"ok": True, "mensagem": "Período excluído."})


@login_required
@require_POST
def api_salvar_medicao(request, bm_id, periodo_id):
    """Salva as quantidades medidas de um período."""
    bm = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    periodo = get_object_or_404(PeriodoMedicao, id=periodo_id, boletim=bm)
    data = _json_body(request)
    linhas = data.get("linhas") or []

    for linha in linhas:
        item_id = linha.get("item_id")
        qtd = _to_decimal(linha.get("quantidade_medida"), default="0")

        try:
            item = ItemContrato.objects.get(id=item_id, boletim=bm)
            med, _ = MedicaoItem.objects.get_or_create(periodo=periodo, item=item)
            med.quantidade_medida = qtd
            med.save(update_fields=["quantidade_medida"])
        except ItemContrato.DoesNotExist:
            continue

    medicoes_dict = {
        m.item_id: m.quantidade_medida or Decimal("0")
        for m in periodo.medicoes.all()
    }

    itens = list(bm.itens.order_by("ordem", "id"))
    acum_ate = _calcular_acumulados(bm, ate_periodo_id=periodo.id)

    linhas_resp = []

    for item in itens:
        qtd_medida = medicoes_dict.get(item.id, Decimal("0"))
        qtd_acum = acum_ate.get(item.id, Decimal("0"))
        qtd_total = item.quantidade_total or Decimal("0")
        pu = item.preco_unitario or Decimal("0")

        valor_total = item.preco_total
        valor_periodo = qtd_medida * pu
        valor_acum = qtd_acum * pu
        saldo = valor_total - valor_acum
        pct = round(float(qtd_acum / qtd_total * 100) if qtd_total else 0, 2)

        linhas_resp.append({
            "item_id": item.id,
            "qtd_medida": float(qtd_medida),
            "qtd_acum": float(qtd_acum),
            "valor_periodo": round(float(valor_periodo), 2),
            "valor_acum": round(float(valor_acum), 2),
            "saldo": round(float(saldo), 2),
            "pct": pct,
        })

    total_periodo = sum(l["valor_periodo"] for l in linhas_resp)

    return JsonResponse({
        "ok": True,
        "mensagem": f"Medições de {periodo.label} salvas.",
        "linhas": linhas_resp,
        "total_periodo": round(total_periodo, 2),
        "periodo": _periodo_to_dict(periodo),
    })


@login_required
@require_GET
def api_dados_consolidado(request, bm_id):
    """Retorna dados consolidados para o relatório."""
    boletim = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    itens = list(boletim.itens.order_by("ordem", "id"))
    periodos = list(boletim.periodos.order_by("numero"))

    qtd_map: dict[int, dict[int, float]] = {item.id: {} for item in itens}

    for p in periodos:
        for m in p.medicoes.all():
            qtd_map.setdefault(m.item_id, {})[p.numero] = float(m.quantidade_medida or 0)

    linhas = []

    for item in itens:
        qtds = [qtd_map[item.id].get(p.numero, 0.0) for p in periodos]
        qtd_acum = sum(qtds)
        pu = float(item.preco_unitario or 0)
        valor_acum = round(qtd_acum * pu, 2)
        valor_total = float(item.preco_total)
        saldo = round(valor_total - valor_acum, 2)
        pct = round((qtd_acum / float(item.quantidade_total) * 100) if item.quantidade_total else 0, 2)

        linhas.append({
            "item_id": item.id,
            "codigo": item.codigo,
            "descricao": item.descricao,
            "unidade": item.unidade,
            "valor_total": round(valor_total, 2),
            "pu": pu,
            "qtds_por_periodo": qtds,
            "qtd_acum": round(qtd_acum, 3),
            "valor_acum": valor_acum,
            "saldo": saldo,
            "pct": pct,
        })

    return JsonResponse({
        "ok": True,
        "periodos": [_periodo_to_dict(p) for p in periodos],
        "linhas": linhas,
    })


@login_required
@require_GET
def api_autocomplete_servico(request):
    termo = (request.GET.get("q") or "").strip()
    qs = _qs_empresa(ProdutoServico.objects, request).filter(ativo=True)

    if termo:
        qs = qs.filter(Q(nome__icontains=termo) | Q(codigo__icontains=termo))

    resultados = [
        {
            "id": s.id,
            "codigo": s.codigo,
            "nome": s.nome,
            "unidade": s.unidade,
            "preco_unitario": float(s.preco_unitario or 0),
        }
        for s in qs.order_by("nome")[:30]
    ]

    return JsonResponse({"ok": True, "resultados": resultados})


@login_required
@require_POST
def api_editar_periodo(request, bm_id):
    """Atualiza as datas de início e fim de um período de medição."""
    bm     = get_object_or_404(_qs_empresa(BoletimMedicao.objects, request), id=bm_id)
    data   = _req_data(request)
    periodo = get_object_or_404(PeriodoMedicao, id=data.get("periodo_id"), boletim=bm)

    data_inicio = data.get("data_inicio")
    data_fim    = data.get("data_fim")

    if not data_inicio or not data_fim:
        return JsonResponse({"ok": False, "erro": "Datas de início e fim são obrigatórias."}, status=400)

    try:
        from datetime import date as _date
        d_ini = _date.fromisoformat(data_inicio)
        d_fim = _date.fromisoformat(data_fim)
        if d_fim < d_ini:
            return JsonResponse({"ok": False, "erro": "Data fim não pode ser anterior à data início."}, status=400)
    except ValueError:
        return JsonResponse({"ok": False, "erro": "Formato de data inválido."}, status=400)

    periodo.data_inicio = d_ini
    periodo.data_fim    = d_fim
    periodo.save(update_fields=["data_inicio", "data_fim"])

    return JsonResponse({
        "ok": True,
        "mensagem": f"{periodo.label} atualizado.",
        "periodo": _periodo_to_dict(periodo),
    })


# ─── DEBUG TEMPORÁRIO — remover após diagnóstico ─────────────────────────────
from django.http import HttpResponse

