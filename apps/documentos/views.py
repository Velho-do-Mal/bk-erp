import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
    qs = Documento.objects.select_related('cliente', 'fornecedor')
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if q:
        qs = qs.filter(titulo__icontains=q)

    docs = list(qs.values(
        'id', 'titulo', 'tipo', 'tags', 'observacoes', 'projeto_nome',
        'cliente__nome', 'fornecedor__nome', 'arquivo_nome',
        'arquivo_tipo', 'enviado_por', 'criado_em', 'data_validade'
    ))

    ctx = {
        'docs_json': json.dumps(docs, default=str),
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
def exportar_documentos(request):
    # CORRIGIDO: referenciava campos inexistentes no modelo (data_documento,
    # ativo) — a exportação sempre lançava FieldError (500).
    qs = _qs_empresa(Documento.objects, request).values('id', 'titulo', 'tipo', 'data_validade')
    rows = [list(r.values()) for r in qs]
    return exportar_csv('documentos.csv', ['ID', 'Título', 'Tipo', 'Data de Validade'], rows)
