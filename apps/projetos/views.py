import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Projeto, ProjetoAcesso


def get_projetos_usuario(user):
    """Retorna queryset de projetos acessíveis ao usuário."""
    if user.is_admin_erp:
        return Projeto.objects.all()
    ids = ProjetoAcesso.objects.filter(usuario=user).values_list('projeto_id', flat=True)
    return Projeto.objects.filter(id__in=ids)


def check_acesso(user, projeto):
    """Verifica se usuário tem acesso ao projeto. Lança Http404 se não."""
    if user.is_admin_erp:
        return True
    if not ProjetoAcesso.objects.filter(usuario=user, projeto=projeto).exists():
        raise Http404


@login_required
def lista(request):
    projetos = get_projetos_usuario(request.user)
    ativos = projetos.filter(encerrado=False)
    encerrados = projetos.filter(encerrado=True)
    return render(request, 'projetos/lista.html', {
        'projetos_ativos': ativos,
        'projetos_encerrados': encerrados,
    })


@login_required
def detalhe(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    check_acesso(request.user, projeto)

    acesso = None
    if not request.user.is_admin_erp:
        acesso = ProjetoAcesso.objects.filter(usuario=request.user, projeto=projeto).first()

    return render(request, 'projetos/detalhe.html', {
        'projeto': projeto,
        'acesso': acesso,
        'tap': projeto.get_tap(),
        'eap_tasks': json.dumps(projeto.get_eap_tasks()),
        'finances': json.dumps(projeto.get_finances()),
        'is_admin': request.user.is_admin_erp,
    })


# ── CRUD (apenas admin) ──────────────────────────────────

@login_required
def novo(request):
    if not request.user.is_admin_erp:
        raise Http404
    if request.method == 'POST':
        nome = request.POST.get('nome', 'Novo Projeto')
        status = request.POST.get('status', 'rascunho')
        data_inicio = request.POST.get('data_inicio') or None
        gerente = request.POST.get('gerente', '')
        patrocinador = request.POST.get('patrocinador', '')
        dados_iniciais = {
            'tap': {
                'nome': nome, 'status': status,
                'dataInicio': str(data_inicio) if data_inicio else '',
                'gerente': gerente, 'patrocinador': patrocinador,
                'objetivo': '', 'escopo': '', 'premissas': '',
                'requisitos': '', 'alteracoesEscopo': [],
            },
            'eapTasks': [], 'finances': [], 'kpis': [],
            'risks': [], 'lessons': [], 'close': {}, 'actionPlan': [],
        }
        p = Projeto.objects.create(
            nome=nome, status=status, data_inicio=data_inicio,
            gerente=gerente, patrocinador=patrocinador, dados=dados_iniciais,
        )
        messages.success(request, f'Projeto "{nome}" criado com sucesso!')
        return redirect('projetos:detalhe', pk=p.pk)
    return render(request, 'projetos/novo.html')


@login_required
def salvar_dados(request, pk):
    """API para salvar JSON completo do projeto (AJAX)."""
    if not request.user.is_admin_erp:
        return JsonResponse({'erro': 'Sem permissão'}, status=403)
    projeto = get_object_or_404(Projeto, pk=pk)
    try:
        dados = json.loads(request.body)
        projeto.dados = dados
        tap = dados.get('tap', {})
        projeto.nome = tap.get('nome', projeto.nome) or projeto.nome
        projeto.status = tap.get('status', projeto.status)
        projeto.gerente = tap.get('gerente', '')
        projeto.patrocinador = tap.get('patrocinador', '')
        data_str = tap.get('dataInicio', '')
        if data_str:
            from datetime import date
            try:
                projeto.data_inicio = date.fromisoformat(data_str)
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
    projeto = get_object_or_404(Projeto, pk=pk)
    projeto.encerrado = True
    projeto.status = 'encerrado'
    projeto.save()
    messages.success(request, f'Projeto "{projeto.nome}" encerrado.')
    return redirect('projetos:lista')


@login_required
def reabrir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404
    projeto = get_object_or_404(Projeto, pk=pk)
    projeto.encerrado = False
    projeto.status = 'execucao'
    projeto.save()
    messages.success(request, f'Projeto "{projeto.nome}" reaberto.')
    return redirect('projetos:lista')


@login_required
def excluir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404
    projeto = get_object_or_404(Projeto, pk=pk)
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
    projeto = get_object_or_404(Projeto, pk=pk)
    clientes = User.objects.filter(perfil='cliente', is_active=True)
    acessos = {a.usuario_id: a for a in ProjetoAcesso.objects.filter(projeto=projeto)}

    if request.method == 'POST':
        usuarios_ids = request.POST.getlist('usuarios')
        # Remove acessos não selecionados
        ProjetoAcesso.objects.filter(projeto=projeto).exclude(usuario_id__in=usuarios_ids).delete()
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
    from datetime import date, timedelta
    import base64
    from .models import ControleDocConfig, DocumentoControle, StatusEventoDocumento

    projeto = get_object_or_404(Projeto, pk=pk)
    check_acesso(request.user, projeto)

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
        eventos = list(StatusEventoDocumento.objects.filter(documento=doc).order_by('data_evento', 'id').values(
            'data_evento', 'status', 'responsavel'
        ))
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
            next_date = eventos[i+1]['data_evento'] if i+1 < len(eventos) else hoje
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
            cfg, _ = ControleDocConfig.objects.get_or_create(projeto=projeto)
            if request.FILES.get('logo_bk'):
                f = request.FILES['logo_bk']
                cfg.logo_bk_nome = f.name
                cfg.logo_bk_tipo = f.content_type or 'image/jpeg'
                cfg.logo_bk_dados = f.read()
            if request.FILES.get('logo_cliente'):
                f = request.FILES['logo_cliente']
                cfg.logo_cliente_nome = f.name
                cfg.logo_cliente_tipo = f.content_type or 'image/jpeg'
                cfg.logo_cliente_dados = f.read()
            cfg.save()
            return JsonResponse({'ok': True})

        data = json.loads(request.body)
        action = data.get('action')

        if action == 'save_meta':
            cfg, _ = ControleDocConfig.objects.get_or_create(projeto=projeto)
            cfg.cliente_nome = data.get('cliente_nome', '').strip()
            cfg.projeto_numero = data.get('projeto_numero', '').strip()
            cfg.projeto_status = data.get('projeto_status', '').strip()
            cfg.save()
            return JsonResponse({'ok': True})

        elif action == 'save_all_docs':
            docs_data = data.get('docs', [])
            saved = 0
            for d in docs_data:
                rid = d.get('id')
                try:
                    obj = DocumentoControle.objects.get(id=rid, projeto=projeto) if rid else DocumentoControle(projeto=projeto)
                except DocumentoControle.DoesNotExist:
                    obj = DocumentoControle(projeto=projeto)

                old_status = obj.status if obj.pk else None
                obj.servico_nome = d.get('codigo', '').strip()
                obj.doc_nome = d.get('atividade', '').strip()
                obj.doc_numero = d.get('doc_numero', '').strip()
                obj.responsavel_bk = d.get('responsavel', '').strip()
                obj.data_inicio = _to_date(d.get('data_inicio'))
                obj.data_conclusao = _to_date(d.get('data_conclusao'))
                obj.percentual_concluido = int(d.get('percentual', 0) or 0)
                obj.status = d.get('status', 'nao_iniciado')
                obj.observacao = d.get('observacao', '').strip()
                obj.save()

                # Registrar evento se status mudou
                new_status = obj.status
                if new_status != old_status:
                    ev_date = obj.data_conclusao if new_status in ('concluido', 'cancelado') else (obj.data_inicio or date.today())
                    StatusEventoDocumento.objects.create(
                        documento=obj,
                        projeto=projeto,
                        data_evento=ev_date or date.today(),
                        status=new_status,
                        responsavel=_responsavel(new_status),
                    )
                saved += 1
            return JsonResponse({'ok': True, 'saved': saved})

        elif action == 'delete_doc':
            DocumentoControle.objects.filter(id=data.get('id'), projeto=projeto).delete()
            return JsonResponse({'ok': True})

    # ── GET ─────────────────────────────────────────────────────────────────
    try:
        cfg = ControleDocConfig.objects.get(projeto=projeto)
        logo_bk_uri = ''
        logo_cli_uri = ''
        if cfg.logo_bk_dados:
            b64 = base64.b64encode(bytes(cfg.logo_bk_dados)).decode()
            logo_bk_uri = f"data:{cfg.logo_bk_tipo or 'image/jpeg'};base64,{b64}"
        if cfg.logo_cliente_dados:
            b64 = base64.b64encode(bytes(cfg.logo_cliente_dados)).decode()
            logo_cli_uri = f"data:{cfg.logo_cliente_tipo or 'image/jpeg'};base64,{b64}"
        meta = {
            'cliente_nome': cfg.cliente_nome,
            'projeto_numero': cfg.projeto_numero,
            'projeto_status': cfg.projeto_status,
            'logo_bk_uri': logo_bk_uri,
            'logo_cliente_uri': logo_cli_uri,
        }
    except ControleDocConfig.DoesNotExist:
        meta = {'cliente_nome': '', 'projeto_numero': '', 'projeto_status': '',
                'logo_bk_uri': '', 'logo_cliente_uri': ''}

    docs_qs = DocumentoControle.objects.filter(projeto=projeto).order_by('id')
    docs = []
    for doc in docs_qs:
        dias_bk, dias_cli = _calcular_dias(doc)
        docs.append({
            'id': doc.id,
            'codigo': doc.servico_nome,
            'atividade': doc.doc_nome,
            'doc_numero': doc.doc_numero,
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
