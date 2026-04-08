import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.projetos.models import Projeto, ProjetoAcesso
from apps.financeiro.models import Transacao
from apps.vendas.models import Proposta, Lead
from apps.compras.models import PedidoCompra


@login_required
def dashboard(request):
    user = request.user
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # --- PROJETOS ---
    if user.is_admin_erp:
        total = Projeto.objects.count()
        ativos = Projeto.objects.filter(encerrado=False).count()
        encerrados = Projeto.objects.filter(encerrado=True).count()
        projetos_recentes = Projeto.objects.filter(encerrado=False)[:5]
    else:
        ids = ProjetoAcesso.objects.filter(usuario=user).values_list('projeto_id', flat=True)
        total = len(ids)
        ativos = Projeto.objects.filter(id__in=ids, encerrado=False).count()
        encerrados = Projeto.objects.filter(id__in=ids, encerrado=True).count()
        projetos_recentes = Projeto.objects.filter(id__in=ids, encerrado=False)[:5]

    # --- FINANCEIRO (KPIs Globais) ---
    receita_total = Transacao.objects.filter(tipo='entrada', status='realizado').aggregate(Sum('valor'))['valor__sum'] or 0
    despesa_total = Transacao.objects.filter(tipo='saida', status='realizado').aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_atual = receita_total - despesa_total
    
    # Dados para gráfico de Rosca (Composição de Despesas por Categoria - Top 5)
    despesas_cat = Transacao.objects.filter(tipo='saida', status='realizado')\
        .values('categoria__nome')\
        .annotate(total=Sum('valor'))\
        .order_by('-total')[:5]
    
    chart_financeiro = {
        'labels': [d['categoria__nome'] or 'Sem Categoria' for d in despesas_cat],
        'values': [float(d['total']) for d in despesas_cat]
    }

    # --- VENDAS (Funil e Conversão) ---
    total_propostas = Proposta.objects.count()
    propostas_aprovadas = Proposta.objects.filter(status='aprovada').count()
    taxa_conversao = (propostas_aprovadas / total_propostas * 100) if total_propostas > 0 else 0
    ticket_medio = Proposta.objects.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    ticket_medio = (ticket_medio / total_propostas) if total_propostas > 0 else 0
    
    # Pipeline de Leads
    leads_estagio = Lead.objects.values('estagio').annotate(qtd=Count('id'), valor=Sum('valor_estimado'))
    pipeline_labels = ['Prospecção', 'Qualificação', 'Proposta', 'Negociação']
    pipeline_map = {
        'prospeccao': 'Prospecção', 'qualificacao': 'Qualificação', 
        'proposta': 'Proposta', 'negociacao': 'Negociação'
    }
    pipeline_data = [0, 0, 0, 0]
    for l in leads_estagio:
        label = pipeline_map.get(l['estagio'])
        if label in pipeline_labels:
            idx = pipeline_labels.index(label)
            pipeline_data[idx] = int(l['qtd'])

    # --- COMPRAS ---
    compras_mes = PedidoCompra.objects.filter(data_pedido__gte=inicio_mes).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    pedidos_pendentes = PedidoCompra.objects.filter(status__in=['aberta', 'aprovacao']).count()

    return render(request, 'core/dashboard.html', {
        'total': total,
        'ativos': ativos,
        'encerrados': encerrados,
        'projetos_recentes': projetos_recentes,
        
        # Financeiro
        'receita_total': receita_total,
        'despesa_total': despesa_total,
        'saldo_atual': saldo_atual,
        'chart_financeiro_json': json.dumps(chart_financeiro),
        
        # Vendas
        'taxa_conversao': round(taxa_conversao, 1),
        'ticket_medio': ticket_medio,
        'pipeline_labels_json': json.dumps(pipeline_labels),
        'pipeline_data_json': json.dumps(pipeline_data),
        
        # Compras
        'compras_mes': compras_mes,
        'pedidos_pendentes': pedidos_pendentes,
    })


def home(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return redirect('accounts:login')
