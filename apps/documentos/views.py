import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .models import Documento
from apps.cadastros.models import Cliente, Fornecedor


@login_required
def lista(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        f = request.FILES['arquivo']
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
        doc.arquivo_dados = f.read()
        doc.enviado_por = request.user.username
        doc.save()
        return JsonResponse({'ok': True, 'id': doc.id})

    if request.method == 'POST':
        data = json.loads(request.body)
        if data.get('action') == 'delete':
            Documento.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})

    # Filtros
    tipo_f = request.GET.get('tipo', '')
    q = request.GET.get('q', '')
    qs = Documento.objects.select_related('cliente', 'fornecedor').defer('arquivo_dados')
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if q:
        qs = qs.filter(titulo__icontains=q)

    docs = list(qs.values(
        'id', 'titulo', 'tipo', 'tags', 'observacoes', 'projeto_nome',
        'cliente__nome', 'fornecedor__nome', 'arquivo_nome',
        'arquivo_tipo', 'enviado_por', 'criado_em'
    ))

    ctx = {
        'docs_json': json.dumps(docs, default=str),
        'clientes': Cliente.objects.filter(ativo=True).values('id', 'nome'),
        'fornecedores': Fornecedor.objects.filter(ativo=True).values('id', 'nome'),
        'tipo_f': tipo_f,
        'q': q,
        'tipos': Documento.TIPO_CHOICES,
    }
    return render(request, 'documentos/lista.html', ctx)


@login_required
def download(request, pk):
    doc = get_object_or_404(Documento, pk=pk)
    if not doc.arquivo_dados:
        from django.http import Http404
        raise Http404
    resp = HttpResponse(bytes(doc.arquivo_dados), content_type=doc.arquivo_tipo or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{doc.arquivo_nome}"'
    return resp
