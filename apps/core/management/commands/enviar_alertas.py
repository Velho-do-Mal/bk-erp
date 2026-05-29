"""
Management command: enviar_alertas
Executa diariamente (Railway Cron às 07h) e envia e-mails de alerta para
administradores da empresa + marcio@bk-engenharia.com.

Alertas disparados:
  1. Contas a vencer amanhã (financeiro)
  2. Projetos com data de conclusão amanhã (prazo)
  3. Documentos de controle com data_conclusao amanhã
  4. Propostas enviadas há 5 dias sem resposta
  5. Pedidos de compra com data_entrega_prevista amanhã
  6. Documentos (GED) com data_validade amanhã

Uso:
  python manage.py enviar_alertas
  python manage.py enviar_alertas --dry-run   # só imprime, não envia
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.db.models import Q


FIXO_EMAIL = 'marcio@bk-engenharia.com'


def _admins_empresa(empresa):
    """Retorna lista de e-mails dos admins ativos de uma empresa."""
    from apps.accounts.models import User
    qs = User.objects.filter(
        empresa=empresa,
        perfil__in=['admin', 'superadmin'],
        is_active=True,
    ).exclude(email='').values_list('email', flat=True)
    return list(qs)


def _destinatarios(empresa):
    """Admins da empresa + e-mail fixo BK (sem duplicatas)."""
    emails = set(_admins_empresa(empresa))
    emails.add(FIXO_EMAIL)
    return list(emails)


def _enviar(assunto, corpo_txt, corpo_html, destinatarios, dry_run=False):
    if not destinatarios:
        return
    if dry_run:
        print(f'  [DRY-RUN] Para: {destinatarios}')
        print(f'  Assunto: {assunto}')
        print(f'  {corpo_txt[:200]}')
        return
    try:
        msg = EmailMultiAlternatives(
            subject=assunto,
            body=corpo_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        msg.attach_alternative(corpo_html, 'text/html')
        msg.send(fail_silently=False)
    except Exception as e:
        print(f'  ERRO ao enviar e-mail: {e}')


HTML_BASE = """
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
  <div style="background:#1e3a8a;padding:20px 24px;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">🔔 {titulo}</h2>
    <p style="color:#bfdbfe;margin:4px 0 0">BK ERP — Alerta Automático</p>
  </div>
  <div style="background:#f8fafc;padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px">
    {corpo}
    <hr style="margin:24px 0;border:none;border-top:1px solid #e2e8f0">
    <p style="color:#94a3b8;font-size:12px;margin:0">
      Este é um e-mail automático do BK ERP. Não responda a esta mensagem.
    </p>
  </div>
</div>
"""


def _html_lista(itens, campos):
    """Gera tabela HTML a partir de lista de dicts."""
    cabecalhos = ''.join(f'<th style="background:#1e3a8a;color:#fff;padding:8px 12px;text-align:left">{c[1]}</th>' for c in campos)
    linhas = ''
    for i, item in enumerate(itens):
        bg = '#fff' if i % 2 == 0 else '#f1f5f9'
        cols = ''.join(f'<td style="padding:8px 12px;border-bottom:1px solid #e2e8f0">{item.get(c[0], "—")}</td>' for c in campos)
        linhas += f'<tr style="background:{bg}">{cols}</tr>'
    return f'<table style="width:100%;border-collapse:collapse"><thead><tr>{cabecalhos}</tr></thead><tbody>{linhas}</tbody></table>'


class Command(BaseCommand):
    help = 'Envia alertas por e-mail para vencimentos do dia seguinte'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Mostra o que seria enviado sem enviar de fato'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        ha_5_dias = hoje - timedelta(days=5)

        self.stdout.write(f'=== enviar_alertas — {hoje} ===')
        if dry_run:
            self.stdout.write('  [MODO DRY-RUN]')

        from apps.saas.models import Empresa
        empresas = Empresa.objects.filter(ativa=True)

        total_emails = 0

        for empresa in empresas:
            dest = _destinatarios(empresa)
            self.stdout.write(f'\nEmpresa: {empresa.nome} — destinatários: {dest}')

            # ── 1. CONTAS A VENCER AMANHÃ ──────────────────────────────────
            try:
                from apps.financeiro.models import Transacao
                contas = list(Transacao.objects.filter(
                    empresa=empresa,
                    data_vencimento=amanha,
                    status='pendente',
                ).values('descricao', 'valor', 'tipo', 'data_vencimento'))

                if contas:
                    itens = [{
                        'descricao': c['descricao'] or '—',
                        'tipo': 'Receita' if c['tipo'] == 'entrada' else 'Despesa',
                        'valor': f"R$ {float(c['valor']):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                        'vencimento': amanha.strftime('%d/%m/%Y'),
                    } for c in contas]

                    tabela = _html_lista(itens, [
                        ('descricao', 'Descrição'), ('tipo', 'Tipo'),
                        ('valor', 'Valor'), ('vencimento', 'Vencimento'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Contas Vencendo Amanhã',
                        corpo=f'<p>As seguintes contas vencem em <strong>{amanha.strftime("%d/%m/%Y")}</strong>:</p>{tabela}'
                    )
                    corpo_txt = f'Contas vencendo em {amanha}: ' + ', '.join(c["descricao"] or "—" for c in contas)
                    _enviar(f'⚠️ [{empresa.nome}] Contas vencendo amanhã ({len(contas)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Contas: {len(contas)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Contas: erro — {e}')

            # ── 2. PROJETOS COM PRAZO AMANHÃ ───────────────────────────────
            try:
                from apps.projetos.models import Projeto
                projetos = list(Projeto.objects.filter(
                    empresa=empresa,
                    data_conclusao=amanha,
                    encerrado=False,
                ).values('nome', 'status', 'gerente', 'data_conclusao'))

                if projetos:
                    itens = [{
                        'nome': p['nome'],
                        'status': p['status'],
                        'gerente': p['gerente'] or '—',
                        'prazo': amanha.strftime('%d/%m/%Y'),
                    } for p in projetos]

                    tabela = _html_lista(itens, [
                        ('nome', 'Projeto'), ('status', 'Status'),
                        ('gerente', 'Gerente'), ('prazo', 'Prazo'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Projetos com Prazo Amanhã',
                        corpo=f'<p>Os seguintes projetos têm prazo em <strong>{amanha.strftime("%d/%m/%Y")}</strong>:</p>{tabela}'
                    )
                    corpo_txt = f'Projetos vencendo em {amanha}: ' + ', '.join(p["nome"] for p in projetos)
                    _enviar(f'🚨 [{empresa.nome}] Projetos com prazo amanhã ({len(projetos)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Projetos: {len(projetos)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Projetos: erro — {e}')

            # ── 3. DOCUMENTOS DE CONTROLE (TAB PROJETOS) VENCENDO AMANHÃ ──
            try:
                from apps.projetos.models import DocumentoControle
                docs_ctrl = list(DocumentoControle.objects.filter(
                    empresa=empresa,
                    data_conclusao=amanha,
                ).exclude(status__in=['concluido', 'cancelado']).values(
                    'doc_nome', 'doc_numero', 'status', 'projeto__nome', 'data_conclusao'
                ))

                if docs_ctrl:
                    itens = [{
                        'doc': d['doc_nome'] or d['doc_numero'] or '—',
                        'projeto': d['projeto__nome'] or '—',
                        'status': d['status'],
                        'prazo': amanha.strftime('%d/%m/%Y'),
                    } for d in docs_ctrl]

                    tabela = _html_lista(itens, [
                        ('doc', 'Documento'), ('projeto', 'Projeto'),
                        ('status', 'Status'), ('prazo', 'Prazo'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Atividades/Documentos Vencendo Amanhã',
                        corpo=f'<p>As seguintes atividades vencem em <strong>{amanha.strftime("%d/%m/%Y")}</strong>:</p>{tabela}'
                    )
                    corpo_txt = f'Documentos de controle vencendo em {amanha}: ' + ', '.join(d["doc_nome"] or "—" for d in docs_ctrl)
                    _enviar(f'📋 [{empresa.nome}] Atividades vencendo amanhã ({len(docs_ctrl)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Docs de controle: {len(docs_ctrl)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Docs de controle: erro — {e}')

            # ── 4. PROPOSTAS SEM RESPOSTA HÁ 5 DIAS ───────────────────────
            try:
                from apps.vendas.models import Proposta
                propostas = list(Proposta.objects.filter(
                    empresa=empresa,
                    data_envio=ha_5_dias,
                    status__in=['enviada', 'em_negociacao'],
                ).values('numero', 'cliente__nome', 'valor_total', 'data_envio', 'status'))

                if propostas:
                    itens = [{
                        'numero': p['numero'] or '—',
                        'cliente': p['cliente__nome'] or '—',
                        'valor': f"R$ {float(p['valor_total'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                        'enviada': p['data_envio'].strftime('%d/%m/%Y') if p['data_envio'] else '—',
                    } for p in propostas]

                    tabela = _html_lista(itens, [
                        ('numero', 'Nº Proposta'), ('cliente', 'Cliente'),
                        ('valor', 'Valor'), ('enviada', 'Enviada em'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Propostas Sem Resposta (5 dias)',
                        corpo=f'<p>As seguintes propostas foram enviadas há 5 dias e ainda não tiveram retorno:</p>{tabela}'
                    )
                    corpo_txt = f'Propostas sem resposta (enviadas em {ha_5_dias}): ' + ', '.join(p["numero"] or "—" for p in propostas)
                    _enviar(f'💼 [{empresa.nome}] Propostas sem resposta há 5 dias ({len(propostas)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Propostas: {len(propostas)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Propostas: erro — {e}')

            # ── 5. PEDIDOS DE COMPRA COM ENTREGA PREVISTA AMANHÃ ──────────
            try:
                from apps.compras.models import PedidoCompra
                compras = list(PedidoCompra.objects.filter(
                    empresa=empresa,
                    data_entrega_prevista=amanha,
                    status__in=['pendente', 'aprovado', 'enviado'],
                ).values('numero', 'fornecedor__nome', 'valor_total', 'data_entrega_prevista', 'status'))

                if compras:
                    itens = [{
                        'numero': c['numero'] or '—',
                        'fornecedor': c['fornecedor__nome'] or '—',
                        'valor': f"R$ {float(c['valor_total'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                        'entrega': amanha.strftime('%d/%m/%Y'),
                    } for c in compras]

                    tabela = _html_lista(itens, [
                        ('numero', 'Nº Pedido'), ('fornecedor', 'Fornecedor'),
                        ('valor', 'Valor'), ('entrega', 'Entrega Prevista'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Compras com Entrega Prevista Amanhã',
                        corpo=f'<p>Os seguintes pedidos têm entrega prevista para <strong>{amanha.strftime("%d/%m/%Y")}</strong>:</p>{tabela}'
                    )
                    corpo_txt = f'Compras com entrega em {amanha}: ' + ', '.join(c["numero"] or "—" for c in compras)
                    _enviar(f'📦 [{empresa.nome}] Compras com entrega amanhã ({len(compras)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Compras: {len(compras)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Compras: erro — {e}')

            # ── 6. DOCUMENTOS (GED) VENCENDO AMANHÃ ───────────────────────
            try:
                from apps.documentos.models import Documento
                docs_ged = list(Documento.objects.filter(
                    empresa=empresa,
                    data_validade=amanha,
                ).values('titulo', 'tipo', 'data_validade'))

                if docs_ged:
                    TIPO_MAP = {
                        'contrato': 'Contrato', 'empresa': 'Doc. Empresa',
                        'seguro': 'Seguro', 'funcionario': 'Doc. Funcionário',
                        'cat': 'CAT', 'procedimento': 'Procedimento',
                        'medicao': 'Medição', 'nota': 'Nota Fiscal',
                        'proposta': 'Proposta', 'outro': 'Outro',
                    }
                    itens = [{
                        'titulo': d['titulo'],
                        'tipo': TIPO_MAP.get(d['tipo'], d['tipo']),
                        'validade': amanha.strftime('%d/%m/%Y'),
                    } for d in docs_ged]

                    tabela = _html_lista(itens, [
                        ('titulo', 'Documento'), ('tipo', 'Tipo'), ('validade', 'Validade'),
                    ])
                    corpo_html = HTML_BASE.format(
                        titulo='Documentos Vencendo Amanhã',
                        corpo=f'<p>Os seguintes documentos vencem em <strong>{amanha.strftime("%d/%m/%Y")}</strong>:</p>{tabela}'
                    )
                    corpo_txt = f'Documentos GED vencendo em {amanha}: ' + ', '.join(d["titulo"] for d in docs_ged)
                    _enviar(f'📄 [{empresa.nome}] Documentos vencendo amanhã ({len(docs_ged)})', corpo_txt, corpo_html, dest, dry_run)
                    total_emails += 1
                    self.stdout.write(f'  ✓ Docs GED: {len(docs_ged)} alerta(s)')
            except Exception as e:
                self.stdout.write(f'  ✗ Docs GED: erro — {e}')

        self.stdout.write(f'\n=== Concluído — {total_emails} e-mail(s) enviado(s) ===')
