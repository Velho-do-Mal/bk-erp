"""
Fonte única de dados do orçamento de uma Proposta.

O dashboard HTML e a planilha Excel leem DAQUI, para que os números
nunca divirjam entre as duas saídas.

Fórmula (idêntica ao calcular() de templates/vendas/proposta_detalhe.html):
    PV = Custo Base / (1 - (impostos% + markup%) / 100)
    Impostos = PV * imposto%        Lucro = PV * markup%
"""


def _f(v, padrao=0.0):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return padrao


def montar_dados_orcamento(proposta):
    d = proposta.dados_orcamento or {}

    # ── Mão de obra (MOB): Qtd × Prazo (meses) × Valor unitário ──
    mob = []
    for r in d.get('mao_de_obra') or []:
        qtd, prazo, unit = _f(r.get('quantidade')), _f(r.get('prazo_meses')), _f(r.get('valor_unitario'))
        mob.append({
            'descricao': (r.get('descricao') or '').strip() or '(sem descrição)',
            'quantidade': qtd, 'prazo_meses': prazo, 'valor_unitario': unit,
            'valor_total': qtd * prazo * unit,
        })

    # ── Custos diretos: Qtd × Repetição × Valor unitário ──
    cd = []
    for r in d.get('custos_diretos') or []:
        qtd, rep, unit = _f(r.get('quantidade')), _f(r.get('repeticao')), _f(r.get('valor_unitario'))
        cd.append({
            'descricao': (r.get('descricao') or '').strip() or '(sem descrição)',
            'quantidade': qtd, 'repeticao': rep, 'valor_unitario': unit,
            'valor_total': qtd * rep * unit,
        })

    custo_mob = sum(r['valor_total'] for r in mob)
    custo_direto = sum(r['valor_total'] for r in cd)
    custo_base = custo_mob + custo_direto

    perc_cfg = d.get('custos_percentuais') or []
    soma_impostos = sum(_f(p.get('percentual')) for p in perc_cfg)
    markup = _f(d.get('markup_percentual'))
    soma_total = soma_impostos + markup
    valido = soma_total < 100

    valor_venda = custo_base / (1 - soma_total / 100) if (custo_base > 0 and valido) else 0.0

    percentuais = []
    for p in perc_cfg:
        pct = _f(p.get('percentual'))
        percentuais.append({
            'nome': (p.get('nome') or '').strip() or '(sem nome)',
            'percentual': pct,
            'valor': valor_venda * pct / 100,
        })
    total_impostos = sum(p['valor'] for p in percentuais)
    lucro = valor_venda * markup / 100

    def _share(v, base):
        return (v / base * 100) if base else 0.0

    for r in mob:
        r['pct_custo'] = _share(r['valor_total'], custo_base)
    for r in cd:
        r['pct_custo'] = _share(r['valor_total'], custo_base)

    # Composição do preço de venda: fecha exatamente em 100%.
    composicao = [
        {'nome': 'Mão de Obra (MOB)', 'valor': custo_mob},
        {'nome': 'Custos Diretos', 'valor': custo_direto},
        {'nome': 'Impostos e Taxas', 'valor': total_impostos},
        {'nome': 'Lucro', 'valor': lucro},
    ]
    for c in composicao:
        c['pct'] = _share(c['valor'], valor_venda)

    return {
        'mob': mob, 'custos_diretos': cd, 'percentuais': percentuais,
        'composicao': composicao,
        'custo_mob': custo_mob, 'custo_direto': custo_direto, 'custo_base': custo_base,
        'soma_impostos': soma_impostos, 'total_impostos': total_impostos,
        'markup': markup, 'soma_total': soma_total, 'valido': valido,
        'valor_venda': valor_venda, 'lucro': lucro,
        'lucro_sobre_custo': _share(lucro, custo_base),
        'receita_liquida': valor_venda - total_impostos,
        'pct_pv_mob': _share(custo_mob, valor_venda),
        'pct_pv_cd': _share(custo_direto, valor_venda),
        'pct_pv_liquida': _share(valor_venda - total_impostos, valor_venda),
        'pct_mob': _share(custo_mob, custo_base),
        'pct_cd': _share(custo_direto, custo_base),
        'vazio': not mob and not cd,
    }
