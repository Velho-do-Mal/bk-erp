import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Cliente, Fornecedor, CentrosDeCusto


@login_required
def clientes(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = Cliente.objects.get(id=rid) if rid else Cliente()
            obj.nome = data.get('nome', '').strip()
            obj.documento = data.get('documento', '').strip()
            obj.email = data.get('email', '').strip()
            obj.telefone = data.get('telefone', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            Cliente.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})
    qs = list(Cliente.objects.values('id', 'nome', 'documento', 'email', 'telefone', 'observacoes', 'ativo'))
    return render(request, 'cadastros/clientes.html', {'clientes_json': json.dumps(qs)})


@login_required
def fornecedores(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = Fornecedor.objects.get(id=rid) if rid else Fornecedor()
            obj.nome = data.get('nome', '').strip()
            obj.documento = data.get('documento', '').strip()
            obj.email = data.get('email', '').strip()
            obj.telefone = data.get('telefone', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            Fornecedor.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})
    qs = list(Fornecedor.objects.values('id', 'nome', 'documento', 'email', 'telefone', 'observacoes', 'ativo'))
    return render(request, 'cadastros/fornecedores.html', {'fornecedores_json': json.dumps(qs)})


@login_required
def centros_custo(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'save':
            rid = data.get('id')
            obj = CentrosDeCusto.objects.get(id=rid) if rid else CentrosDeCusto()
            obj.nome = data.get('nome', '').strip()
            obj.observacoes = data.get('observacoes', '').strip()
            obj.ativo = data.get('ativo', True)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})
        elif action == 'delete':
            CentrosDeCusto.objects.filter(id=data.get('id')).delete()
            return JsonResponse({'ok': True})
    qs = list(CentrosDeCusto.objects.values('id', 'nome', 'observacoes', 'ativo'))
    return render(request, 'cadastros/centros_custo.html', {'centros_json': json.dumps(qs)})
