import json
from apps.core.json_utils import safe_json_dumps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone as dj_timezone
from apps.core.exportacao import exportar_csv
from django.http import HttpResponse, JsonResponse
from .models import Documento
from apps.cadastros.models import Cliente, Fornecedor

def _empresa(request):
    """Retorna a empresa do usuário ou None para superadmin."""
    return getattr(request, 'empresa', None)


def _qs_empresa(qs, request):
    """
    Aplica filtro de empresa ao queryset.
    Se empresa for None (superadmin), retorna o queryset sem filtro.
    """
    empresa = _empresa(request)
    if empresa is None:
        return qs
    return qs.filter(empresa=empresa)




@login_required
def lista(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        from apps.core.validators import validate_upload_view
        f = request.FILES['arquivo']
        err = validate_upload_view(f, 'Arquivo')
        if err:
            return JsonResponse({'ok': False, 'erro': err}, status=400)
        doc = Documento()
        doc.titulo = request.POST.get('titulo', '').strip() or f.name
        doc.tipo = request.POST.get('tipo', 'outro')
        doc.tags = request.POST.get('tags', '').strip()
        doc.observacoes = request.POST.get('observacoes', '').strip()
        doc.projeto_nome = request.POST.get('projeto_nome', '').strip()
        cid = request.POST.get('cliente_id')
        doc.cliente_id = int(cid) if cid else None
        fid = request.POST.get('fornecedor_id')
        doc.fornecedor_id = int(fid) if fid else None
        doc.arquivo_nome = f.name
        doc.arquivo_tipo = f.content_type or 'application/octet-stream'
        doc.arquivo = f
        doc.data_validade = request.POST.get('data_validade') or None
        doc.enviado_por = request.user.username
        if _empresa(request):
            doc.empresa = _empresa(request)
        doc.save()
        return JsonResponse({'ok': True, 'id': doc.id})

    if request.method == 'POST':
        data = json.loads(request.body)
        if data.get('action') == 'delete':
            _qs_empresa(Documento.objects, request).filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    # Filtros
    tipo_f = request.GET.get('tipo', '')
    q = request.GET.get('q', '')
    # CORRIGIDO: a lista mostrava todas as versões de um documento
    # (v1, v2, v3...) misturadas. Agora só mostra a versão vigente de
    # cada grupo; as demais ficam disponíveis pelo histórico (ver
    # `historico()` abaixo), sem serem apagadas.
    # CORRIGIDO (segurança): faltava `_qs_empresa` aqui — a listagem
    # devolvia documentos de TODAS as empresas do SaaS pra qualquer
    # usuário logado (vazamento de dados entre clientes/tenants).
    qs = _qs_empresa(Documento.objects.filter(vigente=True), request).select_related('cliente', 'fornecedor')
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if q:
        qs = qs.filter(titulo__icontains=q)

    docs = list(qs.values(
        'id', 'titulo', 'tipo', 'tags', 'observacoes', 'projeto_nome',
        'cliente_id', 'cliente__nome', 'fornecedor_id', 'fornecedor__nome',
        'arquivo_nome', 'arquivo_tipo', 'enviado_por', 'criado_em', 'data_validade',
        'documento_original_id', 'versao',
    ))

    # CORRIGIDO: "Enviado em" usava a mesma função JS de formatação de
    # `data_validade` (um DateField puro, "YYYY-MM-DD"), mas `criado_em`
    # é um DateTimeField — o front concatenava "T00:00:00" na string já
    # completa do datetime (ex.: "2026-09-03 11:23:45+00:00"), gerando
    # uma data inválida que o navegador interpretava de forma incorreta.
    # Agora a data/hora já vem formatada e convertida pro fuso local
    # (America/Sao_Paulo) do próprio backend, e o front só exibe o texto.
    for d in docs:
        dt = d.get('criado_em')
        d['criado_em'] = dj_timezone.localtime(dt).strftime('%d/%m/%Y %H:%M') if dt else ''

    # Quantas versões cada grupo de documento possui, pra exibir o
    # selo "v2 · 2 versões" e o link de histórico só quando fizer sentido.
    raiz_ids = {d['documento_original_id'] or d['id'] for d in docs}
    contagem_por_raiz = {}
    if raiz_ids:
        for v in Documento.objects.filter(
            Q(pk__in=raiz_ids) | Q(documento_original_id__in=raiz_ids)
        ).values('id', 'documento_original_id'):
            raiz = v['documento_original_id'] or v['id']
            contagem_por_raiz[raiz] = contagem_por_raiz.get(raiz, 0) + 1
    for d in docs:
        raiz = d['documento_original_id'] or d['id']
        d['total_versoes'] = contagem_por_raiz.get(raiz, 1)

    ctx = {
        'docs_json': safe_json_dumps(docs, default=str),
        'clientes': _qs_empresa(Cliente.objects, request).filter(ativo=True).values('id', 'nome'),
        'fornecedores': _qs_empresa(Fornecedor.objects, request).filter(ativo=True).values('id', 'nome'),
        'tipo_f': tipo_f,
        'q': q,
        'tipos': Documento.TIPO_CHOICES,
    }
    return render(request, 'documentos/lista.html', ctx)


@login_required
def download(request, pk):
    empresa = _empresa(request)
    kwargs = {'pk': pk}
    if empresa:
        kwargs['empresa'] = empresa
    doc = get_object_or_404(Documento, **kwargs)
    if not doc.arquivo:
        # CORRIGIDO: registros de Documento com o campo "arquivo" vazio
        # (nenhum arquivo foi de fato anexado ao registro) faziam a rota
        # estourar um Http404 puro, sem nenhuma mensagem — o usuário via a
        # página padrão do Django "Não encontrado", diferente da mensagem
        # amigável de "arquivo não encontrado no armazenamento" usada
        # abaixo. Agora os dois casos (arquivo nunca anexado / arquivo
        # perdido no armazenamento) mostram um aviso e voltam pra lista.
        messages.error(
            request,
            f'O documento "{doc.titulo}" não possui um arquivo anexado. '
            'Reenvie o documento ou contate o suporte.'
        )
        return redirect('documentos:lista')
    try:
        data = doc.arquivo.read()
    except (FileNotFoundError, OSError):
        # CORRIGIDO: quando o registro no banco aponta pra um arquivo que
        # não existe mais no storage (local: apagado, ou perdido num
        # redeploy do filesystem efêmero do Railway quando USE_S3 não está
        # habilitado; S3: chave removida do bucket — django-storages
        # normaliza pra FileNotFoundError nos dois casos, ver
        # S3Boto3Storage._open), .read() lançava a exceção direto pro
        # usuário e a rota dava Erro 500 sem explicar o que aconteceu.
        # Agora avisa e volta pra lista em vez de quebrar a página.
        messages.error(
            request,
            f'O arquivo "{doc.arquivo_nome or doc.titulo}" não foi encontrado no '
            'armazenamento (pode ter sido removido). Reenvie o documento ou contate o suporte.'
        )
        return redirect('documentos:lista')
    resp = HttpResponse(data, content_type=doc.arquivo_tipo or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{doc.arquivo_nome}"'
    return resp


@login_required
def editar(request, pk):
    """Edita os metadados de um documento (não altera o arquivo nem a versão)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido'}, status=405)
    doc = get_object_or_404(_qs_empresa(Documento.objects, request), pk=pk)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'Dados inválidos'}, status=400)

    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return JsonResponse({'ok': False, 'erro': 'Título é obrigatório'}, status=400)

    doc.titulo = titulo
    doc.tipo = data.get('tipo', doc.tipo)
    doc.tags = (data.get('tags') or '').strip()
    doc.observacoes = (data.get('observacoes') or '').strip()
    doc.projeto_nome = (data.get('projeto_nome') or '').strip()
    cid = data.get('cliente_id')
    doc.cliente_id = int(cid) if cid else None
    fid = data.get('fornecedor_id')
    doc.fornecedor_id = int(fid) if fid else None
    doc.data_validade = data.get('data_validade') or None
    doc.save()
    return JsonResponse({'ok': True})


@login_required
def nova_versao(request, pk):
    """
    Cria uma nova versão de um documento existente (ex.: procedimento
    revisado). O registro antigo NÃO é apagado nem sobrescrito — fica
    marcado como não vigente e continua acessível pelo histórico.
    """
    if request.method != 'POST' or not request.FILES.get('arquivo'):
        return JsonResponse({'ok': False, 'erro': 'Envie um arquivo para a nova versão'}, status=400)

    from apps.core.validators import validate_upload_view
    original = get_object_or_404(_qs_empresa(Documento.objects, request), pk=pk)

    f = request.FILES['arquivo']
    err = validate_upload_view(f, 'Arquivo')
    if err:
        return JsonResponse({'ok': False, 'erro': err}, status=400)

    raiz_id = original.documento_original_id or original.id
    grupo = Documento.objects.filter(Q(pk=raiz_id) | Q(documento_original_id=raiz_id))
    ultima_versao = grupo.order_by('-versao').values_list('versao', flat=True).first() or original.versao

    novo = Documento()
    novo.titulo = original.titulo
    novo.tipo = original.tipo
    novo.tags = original.tags
    novo.observacoes = (request.POST.get('observacoes', '').strip()) or original.observacoes
    novo.projeto_nome = original.projeto_nome
    novo.cliente_id = original.cliente_id
    novo.fornecedor_id = original.fornecedor_id
    novo.arquivo_nome = f.name
    novo.arquivo_tipo = f.content_type or 'application/octet-stream'
    novo.arquivo = f
    novo.data_validade = request.POST.get('data_validade') or original.data_validade
    novo.enviado_por = request.user.username
    novo.documento_original_id = raiz_id
    novo.versao = ultima_versao + 1
    novo.vigente = True
    if _empresa(request):
        novo.empresa = _empresa(request)
    novo.save()

    # A nova versão passa a ser a vigente; todas as outras do grupo
    # (raiz + demais versões) deixam de ser vigentes, mas continuam no
    # banco — nada é apagado.
    grupo.update(vigente=False)
    novo.vigente = True
    novo.save(update_fields=['vigente'])

    return JsonResponse({'ok': True, 'id': novo.id})


@login_required
def historico(request, pk):
    """Lista todas as versões (vigente e antigas) do grupo de um documento."""
    doc = get_object_or_404(_qs_empresa(Documento.objects, request), pk=pk)
    raiz_id = doc.documento_original_id or doc.id
    qs = Documento.objects.filter(
        Q(pk=raiz_id) | Q(documento_original_id=raiz_id)
    ).order_by('-versao')

    itens = [{
        'id': d.id,
        'versao': d.versao,
        'titulo': d.titulo,
        'arquivo_nome': d.arquivo_nome,
        'vigente': d.vigente,
        'enviado_por': d.enviado_por,
        'criado_em': dj_timezone.localtime(d.criado_em).strftime('%d/%m/%Y %H:%M') if d.criado_em else '',
    } for d in qs]
    return JsonResponse({'ok': True, 'itens': itens})


@login_required
def exportar_documentos(request):
    # CORRIGIDO: referenciava campos inexistentes no modelo (data_documento,
    # ativo) — a exportação sempre lançava FieldError (500).
    qs = _qs_empresa(Documento.objects, request).values('id', 'titulo', 'tipo', 'data_validade')
    rows = [list(r.values()) for r in qs]
    return exportar_csv('documentos.csv', ['ID', 'Título', 'Tipo', 'Data de Validade'], rows)
