import io
import json
from decimal import Decimal
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from django.contrib import messages

from .models import Proposta, ItemProposta, Lead
from apps.cadastros.models import Cliente


# ─── Helpers ──────────────────────────────────────────────

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


def _proposta_to_dict(p):
    """Serializa uma Proposta para dict (uso na lista e no detalhe)."""
    return {
        'id': p.id,
        'codigo': p.codigo,
        'titulo': p.titulo,
        'cliente_id': p.cliente_id,
        'lead_id': p.lead_id,
        'cliente_nome': p.get_cliente_nome(),
        'cliente_tipo': p.get_cliente_tipo(),
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
        'projeto_ref_id': p.projeto_ref_id,
        'dados_orcamento': p.dados_orcamento or {},
        'itens': [
            {
                'descricao': it.descricao,
                'unidade': it.unidade,
                'quantidade': float(it.quantidade),
                'preco_unitario': float(it.preco_unitario),
                'preco_total': float(it.preco_total),
            }
            for it in p.itens.all()
        ],
    }


def _criar_projeto_a_partir_de_proposta(proposta):
    """
    Cria automaticamente um Projeto quando a proposta e aprovada.
    Passa os dados financeiros do orcamento para o JSONField dados do Projeto.
    """
    try:
        from apps.projetos.models import Projeto

        resultado = proposta.dados_orcamento.get('resultado', {})
        nome_projeto = proposta.projeto_nome or proposta.titulo

        finances = []
        if resultado.get('valor_venda'):
            finances.append({
                'tipo': 'receita',
                'descricao': 'Valor de Venda (Proposta)',
                'valor': resultado['valor_venda'],
            })
        if resultado.get('custo_mob'):
            finances.append({
                'tipo': 'despesa',
                'descricao': 'Mao de Obra',
                'valor': resultado['custo_mob'],
            })
        if resultado.get('custo_direto'):
            finances.append({
                'tipo': 'despesa',
                'descricao': 'Custos Diretos',
                'valor': resultado['custo_direto'],
            })
        for cp in resultado.get('custos_percentuais_calculados', []):
            finances.append({
                'tipo': 'despesa',
                'descricao': cp.get('nome', 'Custo Percentual'),
                'valor': cp.get('valor', 0),
            })

        dados_iniciais = {
            'tap': {
                'nome': nome_projeto,
                'status': 'planejamento',
                'dataInicio': str(proposta.data_emissao) if proposta.data_emissao else '',
                'dataConclusao': str(proposta.data_validade) if proposta.data_validade else '',
                'gerente': '',
                'patrocinador': proposta.get_cliente_nome(),
                'objetivo': proposta.titulo,
                'escopo': proposta.notas_tecnicas or '',
                'premissas': proposta.condicoes_pagamento or '',
                'requisitos': '',
                'prazo': proposta.prazo_execucao or '',
                'proposta_codigo': proposta.codigo,
                'valor_contrato': resultado.get('valor_venda', float(proposta.valor_total)),
                'margem_prevista': resultado.get('margem_lucro', 0),
                'margem_percentual': resultado.get('margem_percentual', 0),
                'alteracoesEscopo': [],
            },
            'eapTasks': [],
            'finances': finances,
            'kpis': [],
            'risks': [],
            'lessons': [],
            'close': {},
            'actionPlan': [],
        }

        projeto = Projeto.objects.create(
            nome=nome_projeto,
            status='planejamento',
            data_inicio=proposta.data_emissao,
            data_conclusao=proposta.data_validade,
            gerente='',
            patrocinador=proposta.get_cliente_nome(),
            dados=dados_iniciais,
        )

        proposta.projeto_ref_id = projeto.pk
        proposta.save(update_fields=['projeto_ref_id'])
        return projeto

    except Exception as e:
        return None


# ─── Lista principal ────────────────────────────────────────────

@login_required
def lista(request):
    """Lista de propostas e leads com KPIs. POST via JSON para CRUD de leads e delete de proposta."""
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save_lead':
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

        elif action == 'delete_proposta':
            Proposta.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

        elif action == 'gerar_financeiro':
            prop = get_object_or_404(Proposta, id=data.get('id'))
            ref = f"PROP:{prop.id}"
            try:
                from apps.financeiro.models import Transacao
                if Transacao.objects.filter(referencia=ref).exists():
                    return JsonResponse({'ok': False, 'msg': 'Ja existe lancamento para esta proposta.'})
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

    propostas = Proposta.objects.select_related('cliente', 'lead').prefetch_related('itens')
    propostas_data = [_proposta_to_dict(p) for p in propostas]

    leads_data = list(Lead.objects.values(
        'id', 'nome', 'empresa', 'contato', 'email', 'estagio', 'valor_estimado', 'observacoes'
    ))
    for l in leads_data:
        l['valor_estimado'] = float(l['valor_estimado'])

    total_valor = Proposta.objects.aggregate(s=Sum('valor_total'))['s'] or 0
    aprovadas = Proposta.objects.filter(status='aprovada').count()
    pipeline_valor = Lead.objects.filter(
        estagio__in=['qualificacao', 'proposta', 'negociacao']
    ).aggregate(s=Sum('valor_estimado'))['s'] or 0

    ctx = {
        'propostas_json': json.dumps(propostas_data),
        'leads_json': json.dumps(leads_data, default=str),
        'total_propostas': Proposta.objects.count(),
        'total_valor': float(total_valor),
        'aprovadas': aprovadas,
        'pipeline_valor': float(pipeline_valor),
    }
    return render(request, 'vendas/lista.html', ctx)


# ─── Detalhe / Nova Proposta ─────────────────────────────────────────

@login_required
def proposta_nova(request):
    """Cria uma nova proposta e redireciona para a pagina de detalhe."""
    from datetime import date as dt
    p = Proposta.objects.create(
        codigo='',
        titulo='Nova Proposta',
        data_emissao=dt.today(),
        status='rascunho',
    )
    return redirect('vendas:proposta_detalhe', pk=p.pk)


@login_required
def proposta_detalhe(request, pk):
    """
    Pagina dedicada da proposta com duas abas:
    - Aba 1: Calculo do Orcamento (MOB, custos diretos, percentuais, resultado, graficos)
    - Aba 2: Proposta (itens + exportar Word)

    POST JSON actions:
    - save_cabecalho
    - save_orcamento
    - save_itens
    - mudar_status
    """
    proposta = get_object_or_404(Proposta, pk=pk)

    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save_cabecalho':
            proposta.codigo = data.get('codigo', '').strip()
            proposta.titulo = data.get('titulo', '').strip()
            proposta.projeto_nome = data.get('projeto_nome', '').strip()
            proposta.data_emissao = _to_date(data.get('data_emissao')) or date.today()
            proposta.data_validade = _to_date(data.get('data_validade'))
            proposta.condicoes_pagamento = data.get('condicoes_pagamento', '').strip()
            proposta.prazo_execucao = data.get('prazo_execucao', '').strip()
            proposta.observacoes = data.get('observacoes', '').strip()
            proposta.notas_tecnicas = data.get('notas_tecnicas', '').strip()

            tipo_origem = data.get('origem_tipo', '')
            origem_id = data.get('origem_id')
            if tipo_origem == 'cliente':
                proposta.cliente_id = int(origem_id) if origem_id else None
                proposta.lead_id = None
            elif tipo_origem == 'lead':
                proposta.lead_id = int(origem_id) if origem_id else None
                proposta.cliente_id = None
            else:
                proposta.cliente_id = None
                proposta.lead_id = None

            proposta.save()
            return JsonResponse({'ok': True, 'cliente_nome': proposta.get_cliente_nome()})

        elif action == 'save_orcamento':
            proposta.dados_orcamento = data.get('dados_orcamento', {})
            resultado = proposta.dados_orcamento.get('resultado', {})
            valor_venda = resultado.get('valor_venda', 0)
            if valor_venda:
                proposta.valor_total = Decimal(str(valor_venda))
            proposta.save(update_fields=['dados_orcamento', 'valor_total'])
            return JsonResponse({'ok': True})

        elif action == 'save_itens':
            itens = data.get('itens', [])
            proposta.itens.all().delete()
            total = Decimal('0')
            for i, it in enumerate(itens):
                qty = _to_dec(it.get('quantidade', 1))
                preco = _to_dec(it.get('preco_unitario', 0))
                subtotal = qty * preco
                total += subtotal
                ItemProposta.objects.create(
                    proposta=proposta,
                    descricao=it.get('descricao', ''),
                    unidade=it.get('unidade', ''),
                    quantidade=qty,
                    preco_unitario=preco,
                    preco_total=subtotal,
                    ordem=i,
                )
            if not proposta.dados_orcamento.get('resultado', {}).get('valor_venda'):
                proposta.valor_total = total
                proposta.save(update_fields=['valor_total'])
            return JsonResponse({'ok': True, 'valor_total': float(proposta.valor_total)})

        elif action == 'mudar_status':
            novo_status = data.get('status', '')
            status_validos = [s[0] for s in Proposta.STATUS_CHOICES]
            if novo_status not in status_validos:
                return JsonResponse({'ok': False, 'msg': 'Status invalido.'})

            proposta.status = novo_status
            proposta.save(update_fields=['status'])

            projeto_id = None
            msg_extra = ''
            if novo_status == 'aprovada' and not proposta.projeto_ref_id:
                projeto = _criar_projeto_a_partir_de_proposta(proposta)
                if projeto:
                    projeto_id = projeto.pk
                    msg_extra = f' Projeto #{projeto.pk} criado em Gestao de Projetos.'

            return JsonResponse({
                'ok': True,
                'status': proposta.status,
                'projeto_id': projeto_id,
                'msg': f'Status atualizado para "{proposta.get_status_display()}".{msg_extra}',
            })

    clientes = list(Cliente.objects.filter(ativo=True).values('id', 'nome'))
    leads = list(Lead.objects.values('id', 'nome', 'empresa'))
    proposta_data = _proposta_to_dict(proposta)

    ctx = {
        'proposta': proposta,
        'proposta_json': json.dumps(proposta_data),
        'clientes_json': json.dumps(clientes),
        'leads_json': json.dumps(leads),
        'status_choices': Proposta.STATUS_CHOICES,
    }
    return render(request, 'vendas/proposta_detalhe.html', ctx)


# ─── Exportar Word ────────────────────────────────────────────────────

@login_required
def exportar_word(request, pk):
    """
    Gera um arquivo .docx com a proposta comercial formatada.
    Usa apenas dados do cabecalho e ItemProposta - NAO inclui dados de orcamento.
    """
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    proposta = get_object_or_404(Proposta, pk=pk)
    itens = proposta.itens.all()

    doc = Document()

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    titulo_para = doc.add_paragraph()
    titulo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo_para.add_run('BK ENGENHARIA E TECNOLOGIA')
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    sub_para = doc.add_paragraph()
    sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_para.add_run('PROPOSTA TECNICA E COMERCIAL')
    sub_run.bold = True
    sub_run.font.size = Pt(13)

    doc.add_paragraph()

    tabela_info = doc.add_table(rows=0, cols=2)
    tabela_info.style = 'Table Grid'

    def add_info_row(label, value):
        row = tabela_info.add_row()
        cell_label = row.cells[0]
        cell_value = row.cells[1]
        cell_label.text = label
        cell_value.text = str(value) if value else '—'
        cell_label.paragraphs[0].runs[0].bold = True
        cell_label.width = Cm(5)

    add_info_row('Codigo:', proposta.codigo or '—')
    add_info_row('Titulo:', proposta.titulo)
    add_info_row('Cliente:', proposta.get_cliente_nome() or '—')
    add_info_row('Projeto:', proposta.projeto_nome or '—')
    add_info_row('Data de Emissao:', proposta.data_emissao.strftime('%d/%m/%Y') if proposta.data_emissao else '—')
    add_info_row('Validade:', proposta.data_validade.strftime('%d/%m/%Y') if proposta.data_validade else '—')
    add_info_row('Prazo de Execucao:', proposta.prazo_execucao or '—')
    add_info_row('Condicoes de Pagamento:', proposta.condicoes_pagamento or '—')

    doc.add_paragraph()

    if proposta.notas_tecnicas:
        h = doc.add_paragraph('ESCOPO DO SERVICO')
        h.runs[0].bold = True
        h.runs[0].font.size = Pt(12)
        doc.add_paragraph(proposta.notas_tecnicas)
        doc.add_paragraph()

    h2 = doc.add_paragraph('ITENS DA PROPOSTA')
    h2.runs[0].bold = True
    h2.runs[0].font.size = Pt(12)

    headers = ['#', 'Descricao', 'Unid.', 'Qtd.', 'Valor Unit. (R$)', 'Total (R$)']
    tabela_itens = doc.add_table(rows=1, cols=6)
    tabela_itens.style = 'Table Grid'

    hdr_row = tabela_itens.rows[0]
    for i, h_text in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    total_geral = Decimal('0')
    for idx, item in enumerate(itens, start=1):
        row = tabela_itens.add_row()
        row.cells[0].text = str(idx)
        row.cells[1].text = item.descricao
        row.cells[2].text = item.unidade or '—'
        row.cells[3].text = f'{item.quantidade:.2f}'
        row.cells[4].text = f'R$ {item.preco_unitario:,.2f}'
        row.cells[5].text = f'R$ {item.preco_total:,.2f}'
        total_geral += item.preco_total

    row_total = tabela_itens.add_row()
    row_total.cells[4].text = 'TOTAL:'
    row_total.cells[4].paragraphs[0].runs[0].bold = True
    row_total.cells[5].text = f'R$ {total_geral:,.2f}'
    row_total.cells[5].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()

    if proposta.observacoes:
        h3 = doc.add_paragraph('OBSERVACOES')
        h3.runs[0].bold = True
        h3.runs[0].font.size = Pt(12)
        doc.add_paragraph(proposta.observacoes)
        doc.add_paragraph()

    doc.add_paragraph()
    doc.add_paragraph('_' * 40)
    doc.add_paragraph('BK Engenharia e Tecnologia')
    doc.add_paragraph(f'Emitido em: {date.today().strftime("%d/%m/%Y")}')

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nome_arquivo = f'Proposta_{proposta.codigo or proposta.pk}.docx'.replace('/', '-').replace(' ', '_')
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return response
