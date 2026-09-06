import json
from apps.core.json_utils import safe_json_dumps
from datetime import date

from apps.core.tenant import tenant_get_or_404
from apps.core.validators import validate_upload_view
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, FileResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import Projeto, ProjetoAcesso


def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    """
    Aplica filtro multiempresa de forma segura.

    - Se o model tem campo empresa: filtra empresa=empresa.
    - Se o model tem campo projeto: filtra projeto__empresa=empresa.
    - Se o model tem campo documento: filtra documento__projeto__empresa=empresa.
    """
    empresa = _empresa(request)

    if empresa is None:
        return qs

    model = qs.model
    field_names = {f.name for f in model._meta.get_fields()}

    if 'empresa' in field_names:
        return qs.filter(empresa=empresa)

    if 'projeto' in field_names:
        return qs.filter(projeto__empresa=empresa)

    if 'documento' in field_names:
        return qs.filter(documento__projeto__empresa=empresa)

    return qs


def get_projetos_usuario(request):
    """Retorna queryset de projetos acessíveis ao usuário."""
    user = request.user

    if user.is_admin_erp:
        return _qs_empresa(Projeto.objects, request)

    ids = (
        _qs_empresa(ProjetoAcesso.objects, request)
        .filter(usuario=user)
        .values_list('projeto_id', flat=True)
    )
    return _qs_empresa(Projeto.objects, request).filter(id__in=ids)


def check_acesso(request, projeto):
    """Verifica se usuário tem acesso ao projeto. Lança Http404 se não."""
    user = request.user

    if user.is_admin_erp:
        return True

    if not (
        _qs_empresa(ProjetoAcesso.objects, request)
        .filter(usuario=user, projeto=projeto)
        .exists()
    ):
        raise Http404

    return True


@login_required
def lista(request):
    projetos = get_projetos_usuario(request)
    ativos = projetos.filter(encerrado=False)
    encerrados = projetos.filter(encerrado=True)

    return render(request, 'projetos/lista.html', {
        'projetos_ativos': ativos,
        'projetos_encerrados': encerrados,
        'today': date.today(),
    })


@login_required
def detalhe(request, pk):
    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)

    acesso = None
    if not request.user.is_admin_erp:
        acesso = (
            _qs_empresa(ProjetoAcesso.objects, request)
            .filter(usuario=request.user, projeto=projeto)
            .first()
        )

    tap = projeto.get_tap()

    return render(request, 'projetos/detalhe.html', {
        'projeto': projeto,
        'acesso': acesso,
        'tap': tap,
        'eap_tasks': safe_json_dumps(projeto.get_eap_tasks()),
        'finances': safe_json_dumps(projeto.get_finances()),
        # Mesmo motivo do eap_tasks/finances acima: nunca embutir esses
        # valores crus (com |safe) direto no <script> do template — um
        # risco, licao aprendida ou item de plano de acao com
        # "</script><script>...evil...</script>" digitado pelo usuario
        # quebraria a tag e executaria HTML/JS arbitrário no navegador de
        # quem abrir o projeto. safe_json_dumps() escapa isso.
        'kpis': safe_json_dumps(projeto.dados.get('kpis', [])),
        'risks': safe_json_dumps(projeto.dados.get('risks', [])),
        'lessons': safe_json_dumps(projeto.dados.get('lessons', [])),
        'close_data': safe_json_dumps(projeto.dados.get('close', {})),
        'action_plan': safe_json_dumps(projeto.dados.get('actionPlan', [])),
        'alteracoes_escopo': safe_json_dumps(tap.get('alteracoesEscopo', [])),
        'is_admin': request.user.is_admin_erp,
    })


@login_required
def relatorio_docx(request, pk):
    """Gera o Relatório Geral do projeto em Word (.docx) — mesmos dados do
    relatório HTML (impressão no navegador), formatado pra apresentação a
    patrocinador/gestor: organograma, EAP, Gantt, financeiro e riscos."""
    from django.http import HttpResponse
    from .relatorio_docx import gerar_relatorio_docx

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)

    buf = gerar_relatorio_docx(projeto)
    nome_arquivo = f"Relatorio_{projeto.nome}_{date.today().isoformat()}.docx"
    nome_arquivo = "".join(c if (c.isalnum() or c in "._-") else " " for c in nome_arquivo)
    nome_arquivo = "_".join(nome_arquivo.split())

    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return response


# ── CRUD (apenas admin) ──────────────────────────────────

@login_required
def novo(request):
    if not request.user.is_admin_erp:
        raise Http404

    if request.method == 'POST':
        nome = request.POST.get('nome', 'Novo Projeto')
        status = request.POST.get('status', 'rascunho')
        data_inicio = request.POST.get('data_inicio') or None
        data_conclusao = request.POST.get('data_conclusao') or None
        gerente = request.POST.get('gerente', '')
        patrocinador = request.POST.get('patrocinador', '')

        dados_iniciais = {
            'tap': {
                'nome': nome,
                'status': status,
                'dataInicio': str(data_inicio) if data_inicio else '',
                'dataConclusao': str(data_conclusao) if data_conclusao else '',
                'gerente': gerente,
                'patrocinador': patrocinador,
                'objetivo': '',
                'escopo': '',
                'premissas': '',
                'requisitos': '',
                'alteracoesEscopo': [],
            },
            'eapTasks': [],
            'finances': [],
            'kpis': [],
            'risks': [],
            'lessons': [],
            'close': {},
            'actionPlan': [],
            'docs': [],
        }

        p = Projeto.objects.create(
            empresa=_empresa(request),
            nome=nome,
            status=status,
            data_inicio=data_inicio,
            data_conclusao=data_conclusao,
            gerente=gerente,
            patrocinador=patrocinador,
            dados=dados_iniciais,
        )

        messages.success(request, f'Projeto "{nome}" criado com sucesso!')
        return redirect('projetos:detalhe', pk=p.pk)

    return render(request, 'projetos/novo.html')


@login_required
def salvar_dados(request, pk):
    """API para salvar JSON do projeto (AJAX), preservando dados já existentes."""
    if not request.user.is_admin_erp:
        return JsonResponse({'erro': 'Sem permissão'}, status=403)

    projeto = tenant_get_or_404(Projeto, request, pk=pk)

    try:
        dados = json.loads(request.body or '{}')

        if not isinstance(dados, dict):
            return JsonResponse({'erro': 'Payload inválido.'}, status=400)

        dados_atuais = projeto.dados or {}
        dados_atuais.update(dados)

        projeto.dados = dados_atuais
        tap = projeto.dados.get('tap', {}) or {}

        projeto.nome = tap.get('nome', projeto.nome) or projeto.nome
        projeto.status = tap.get('status', projeto.status)
        projeto.gerente = tap.get('gerente', '')
        projeto.patrocinador = tap.get('patrocinador', '')

        data_ini_str = tap.get('dataInicio', '')
        if data_ini_str:
            try:
                projeto.data_inicio = date.fromisoformat(str(data_ini_str)[:10])
            except Exception:
                pass

        data_fim_str = tap.get('dataConclusao', '')
        if data_fim_str:
            try:
                projeto.data_conclusao = date.fromisoformat(str(data_fim_str)[:10])
            except Exception:
                pass

        projeto.save()
        return JsonResponse({'ok': True, 'nome': projeto.nome})

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)


@login_required
def encerrar(request, pk):
    if not request.user.is_admin_erp:
        raise Http404

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    projeto.encerrado = True
    projeto.status = 'encerrado'
    projeto.save()

    messages.success(request, f'Projeto "{projeto.nome}" encerrado.')
    return redirect('projetos:lista')


@login_required
def reabrir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    projeto.encerrado = False
    projeto.status = 'execucao'
    projeto.save()

    messages.success(request, f'Projeto "{projeto.nome}" reaberto.')
    return redirect('projetos:lista')


@login_required
def excluir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    nome = projeto.nome
    projeto.delete()

    messages.success(request, f'Projeto "{nome}" excluído.')
    return redirect('projetos:lista')


@login_required
def gerenciar_acessos(request, pk):
    """Tela para liberar/revogar acesso de clientes ao projeto."""
    if not request.user.is_admin_erp:
        raise Http404

    from apps.accounts.models import User

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    clientes = _qs_empresa(User.objects, request).filter(perfil='cliente', is_active=True)
    acessos = {
        a.usuario_id: a
        for a in _qs_empresa(ProjetoAcesso.objects, request).filter(projeto=projeto)
    }

    if request.method == 'POST':
        usuarios_ids = request.POST.getlist('usuarios')

        # Remove acessos não selecionados
        (
            _qs_empresa(ProjetoAcesso.objects, request)
            .filter(projeto=projeto)
            .exclude(usuario_id__in=usuarios_ids)
            .delete()
        )

        # Cria novos acessos
        for uid in usuarios_ids:
            ProjetoAcesso.objects.get_or_create(projeto=projeto, usuario_id=uid)

        messages.success(request, 'Acessos atualizados!')
        return redirect('projetos:detalhe', pk=pk)

    return render(request, 'projetos/acessos.html', {
        'projeto': projeto,
        'clientes': clientes,
        'acessos': acessos,
    })


# ── Controle de Documentos ──────────────────────────────────────────────────

@login_required
def controle_docs(request, pk):
    """CRUD + histórico de status para controle de documentos do projeto."""
    from .models import ControleDocConfig, DocumentoControle, StatusEventoDocumento

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)

    def _to_date(v):
        if not v:
            return None
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            return None

    def _responsavel(status):
        """Retorna 'CLIENTE' se em análise, 'BK' caso contrário."""
        return 'CLIENTE' if status == 'em_analise' else 'BK'

    def _calcular_dias(doc):
        """Calcula dias BK e dias CLIENTE via histórico de eventos."""
        eventos = list(
            _qs_empresa(StatusEventoDocumento.objects, request)
            .filter(documento=doc)
            .order_by('data_evento', 'id')
            .values('data_evento', 'status', 'responsavel')
        )

        if not eventos:
            # Estimar pelo status atual e datas
            ini = doc.data_inicio or date.today()
            hoje = date.today()
            fim = doc.data_conclusao if doc.status in ('concluido', 'cancelado') else hoje
            dias = max(0, (fim - ini).days)

            if doc.status == 'em_analise':
                return 0, dias

            return dias, 0

        dias_bk = 0
        dias_cli = 0
        hoje = date.today()

        for i, ev in enumerate(eventos):
            ev_date = ev['data_evento']
            next_date = eventos[i + 1]['data_evento'] if i + 1 < len(eventos) else hoje
            delta = max(0, (next_date - ev_date).days)

            if ev['responsavel'] == 'CLIENTE':
                dias_cli += delta
            else:
                dias_bk += delta

        return dias_bk, dias_cli

    # ── POST ────────────────────────────────────────────────────────────────
    if request.method == 'POST':
        if not request.user.is_admin_erp:
            return JsonResponse({'erro': 'Sem permissão'}, status=403)

        # Logo upload (multipart)
        if request.FILES.get('logo_bk') or request.FILES.get('logo_cliente'):
            for campo in ('logo_bk', 'logo_cliente'):
                arq = request.FILES.get(campo)
                if arq:
                    erro = validate_upload_view(arq, field_label=campo.replace('_', ' ').title())
                    if erro:
                        return JsonResponse({'erro': erro}, status=400)

            cfg, _ = ControleDocConfig.objects.get_or_create(projeto=projeto)

            if request.FILES.get('logo_bk'):
                f = request.FILES['logo_bk']
                cfg.logo_bk_nome = f.name
                cfg.logo_bk_tipo = f.content_type or 'image/jpeg'
                cfg.logo_bk.save(f.name, f, save=False)

            if request.FILES.get('logo_cliente'):
                f = request.FILES['logo_cliente']
                cfg.logo_cliente_nome = f.name
                cfg.logo_cliente_tipo = f.content_type or 'image/jpeg'
                cfg.logo_cliente.save(f.name, f, save=False)

            cfg.save()
            return JsonResponse({'ok': True})

        data = json.loads(request.body or '{}')
        action = data.get('action')

        if action == 'save_meta':
            cfg, _ = ControleDocConfig.objects.get_or_create(projeto=projeto)
            cfg.cliente_nome = data.get('cliente_nome', '').strip()
            cfg.projeto_numero = data.get('projeto_numero', '').strip()
            cfg.projeto_status = data.get('projeto_status', '').strip()
            cfg.revisao = data.get('revisao', '').strip()
            cfg.save()
            return JsonResponse({'ok': True})

        if action == 'save_all_docs':
            docs_data = data.get('docs', [])
            saved = 0

            for d in docs_data:
                rid = d.get('id')

                # IDs de compatibilidade do legado podem vir como "legacy-0".
                # Nesse caso, não tentamos buscar por ID numérico; criamos novo registro.
                try:
                    rid_int = int(rid) if rid not in (None, '', False) else None
                except (TypeError, ValueError):
                    rid_int = None

                try:
                    obj = (
                        DocumentoControle.objects.get(id=rid_int, projeto=projeto)
                        if rid_int
                        else DocumentoControle(projeto=projeto)
                    )
                except DocumentoControle.DoesNotExist:
                    obj = DocumentoControle(projeto=projeto)

                old_status = obj.status if obj.pk else None

                obj.servico_nome = d.get('codigo', '').strip()
                obj.doc_nome = d.get('atividade', '').strip()
                obj.doc_numero = d.get('doc_numero', '').strip()
                obj.revisao = d.get('revisao', '').strip()
                obj.responsavel_bk = d.get('responsavel', '').strip()
                obj.data_inicio = _to_date(d.get('data_inicio'))
                obj.data_conclusao = _to_date(d.get('data_conclusao'))

                try:
                    obj.percentual_concluido = int(d.get('percentual', 0) or 0)
                except (TypeError, ValueError):
                    obj.percentual_concluido = 0

                obj.status = d.get('status', 'nao_iniciado') or 'nao_iniciado'
                obj.observacao = d.get('observacao', '').strip()
                obj.save()

                # Registrar evento se status mudou
                new_status = obj.status
                if new_status != old_status:
                    ev_date = (
                        obj.data_conclusao
                        if new_status in ('concluido', 'cancelado')
                        else (obj.data_inicio or date.today())
                    )
                    StatusEventoDocumento.objects.create(
                        documento=obj,
                        projeto=projeto,
                        data_evento=ev_date or date.today(),
                        status=new_status,
                        responsavel=_responsavel(new_status),
                    )

                saved += 1

            return JsonResponse({'ok': True, 'saved': saved})

        if action == 'delete_doc':
            _qs_empresa(DocumentoControle.objects, request).filter(
                id=data.get('id'),
                projeto=projeto,
            ).delete()
            return JsonResponse({'ok': True})

        return JsonResponse({'erro': 'Ação inválida.'}, status=400)

    # ── GET ─────────────────────────────────────────────────────────────────
    try:
        cfg = ControleDocConfig.objects.get(projeto=projeto)
        logo_bk_uri = cfg.logo_bk.url if cfg.logo_bk else ''
        logo_cli_uri = cfg.logo_cliente.url if cfg.logo_cliente else ''

        meta = {
            'cliente_nome': cfg.cliente_nome,
            'projeto_numero': cfg.projeto_numero,
            'revisao': cfg.revisao,
            'projeto_status': cfg.projeto_status,
            'logo_bk_uri': logo_bk_uri,
            'logo_cliente_uri': logo_cli_uri,
        }

    except ControleDocConfig.DoesNotExist:
        meta = {
            'cliente_nome': '',
            'projeto_numero': '',
            'revisao': '',
            'projeto_status': '',
            'logo_bk_uri': '',
            'logo_cliente_uri': '',
        }

    docs_qs = (
        _qs_empresa(DocumentoControle.objects, request)
        .filter(projeto=projeto)
        .order_by('id')
    )

    docs = []

    # ---------------------------------------------------------------------
    # COMPATIBILIDADE URGENTE:
    # Se a nova tabela DocumentoControle estiver vazia, tenta carregar
    # os documentos antigos salvos no JSON projeto.dados["docs"].
    # ---------------------------------------------------------------------
    try:
        legacy_docs = (projeto.dados or {}).get('docs', []) or []
    except Exception:
        legacy_docs = []

    if not docs_qs.exists() and legacy_docs:
        for idx, d in enumerate(legacy_docs):
            docs.append({
                'id': d.get('id') or f'legacy-{idx}',
                'codigo': d.get('codigo') or d.get('servico_nome') or d.get('servico') or '',
                'atividade': d.get('atividade') or d.get('doc_nome') or d.get('nome') or d.get('descricao') or '',
                'doc_numero': d.get('doc_numero') or d.get('numero') or d.get('documento') or '',
                'revisao': d.get('revisao') or d.get('rev') or '',
                'responsavel': d.get('responsavel') or d.get('responsavel_bk') or '',
                'data_inicio': d.get('data_inicio') or d.get('dataInicio') or '',
                'data_conclusao': d.get('data_conclusao') or d.get('dataConclusao') or '',
                'percentual': d.get('percentual') or d.get('percentual_concluido') or d.get('progresso') or 0,
                'status': d.get('status') or 'nao_iniciado',
                'observacao': d.get('observacao') or d.get('obs') or '',
                'dias_bk': d.get('dias_bk') or 0,
                'dias_cli': d.get('dias_cli') or 0,
            })

        return JsonResponse({'meta': meta, 'docs': docs})

    for doc in docs_qs:
        dias_bk, dias_cli = _calcular_dias(doc)
        docs.append({
            'id': doc.id,
            'codigo': doc.servico_nome,
            'atividade': doc.doc_nome,
            'doc_numero': doc.doc_numero,
            'revisao': doc.revisao,
            'responsavel': doc.responsavel_bk,
            'data_inicio': str(doc.data_inicio) if doc.data_inicio else '',
            'data_conclusao': str(doc.data_conclusao) if doc.data_conclusao else '',
            'percentual': doc.percentual_concluido,
            'status': doc.status,
            'observacao': doc.observacao,
            'dias_bk': dias_bk,
            'dias_cli': dias_cli,
        })

    return JsonResponse({'meta': meta, 'docs': docs})


# ─── Anexos por documento ────────────────────────────────────────────────────

@login_required
def api_anexos(request, pk, doc_id):
    """GET: lista anexos do documento. POST (multipart): faz upload de um arquivo."""
    from .models import DocumentoControle, AnexoDocumento

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)
    doc = get_object_or_404(DocumentoControle, id=doc_id, projeto=projeto)

    if request.method == 'POST':
        if not request.user.is_admin_erp:
            return JsonResponse({'erro': 'Sem permissão'}, status=403)

        f = request.FILES.get('arquivo')
        if not f:
            return JsonResponse({'erro': 'Nenhum arquivo enviado.'}, status=400)

        erro = validate_upload_view(f, field_label='Anexo')
        if erro:
            return JsonResponse({'erro': erro}, status=400)

        anexo = AnexoDocumento.objects.create(
            documento=doc,
            nome_original=f.name,
            arquivo=f,
            tamanho=f.size,
            enviado_por=request.user,
        )

        return JsonResponse({
            'ok': True,
            'anexo': {
                'id': anexo.id,
                'nome': anexo.nome_original,
                'tamanho': anexo.tamanho,
                'criado_em': anexo.criado_em.strftime('%d/%m/%Y %H:%M'),
                'enviado_por': str(anexo.enviado_por) if anexo.enviado_por else '',
                'download_url': f'/projetos/{pk}/controle-docs/anexos/{anexo.id}/download/',
                'excluir_url': f'/projetos/{pk}/controle-docs/anexos/{anexo.id}/excluir/',
            },
        })

    anexos = _qs_empresa(AnexoDocumento.objects, request).filter(documento=doc)

    return JsonResponse({
        'ok': True,
        'anexos': [
            {
                'id': a.id,
                'nome': a.nome_original,
                'tamanho': a.tamanho,
                'criado_em': a.criado_em.strftime('%d/%m/%Y %H:%M'),
                'enviado_por': str(a.enviado_por) if a.enviado_por else '',
                'download_url': f'/projetos/{pk}/controle-docs/anexos/{a.id}/download/',
                'excluir_url': f'/projetos/{pk}/controle-docs/anexos/{a.id}/excluir/',
            }
            for a in anexos
        ],
    })


@login_required
@require_POST
def excluir_anexo(request, pk, anexo_id):
    """Remove um anexo."""
    from .models import AnexoDocumento

    if not request.user.is_admin_erp:
        return JsonResponse({'erro': 'Sem permissão'}, status=403)

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)

    anexo = get_object_or_404(
        AnexoDocumento,
        id=anexo_id,
        documento__projeto=projeto,
    )

    # Remove arquivo físico e registro
    try:
        anexo.arquivo.delete(save=False)
    except Exception:
        pass

    anexo.delete()
    return JsonResponse({'ok': True})


@login_required
def download_anexo(request, pk, anexo_id):
    """Faz download de um anexo."""
    from .models import AnexoDocumento

    projeto = tenant_get_or_404(Projeto, request, pk=pk)
    check_acesso(request, projeto)

    anexo = get_object_or_404(
        AnexoDocumento,
        id=anexo_id,
        documento__projeto=projeto,
    )

    try:
        response = FileResponse(
            anexo.arquivo.open('rb'),
            as_attachment=True,
            filename=anexo.nome_original,
        )
        return response
    except Exception:
        raise Http404('Arquivo não encontrado.')
