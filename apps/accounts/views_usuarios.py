import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from apps.accounts.decorators import admin_required
from apps.accounts.models import User


@admin_required
def usuarios(request):
    empresa = getattr(request, 'empresa', None)

    if request.method == 'POST':
        data  = json.loads(request.body)
        action = data.get('action')

        if action == 'save':
            nome    = data.get('nome', '').strip()
            username = data.get('username', '').strip()
            email   = data.get('email', '').strip()
            perfil  = data.get('perfil', 'cliente')
            senha   = data.get('senha', '').strip()
            ativo   = data.get('ativo', True)
            uid     = data.get('id')

            if not nome:     return JsonResponse({'ok': False, 'error': 'Nome é obrigatório.'})
            if not username: return JsonResponse({'ok': False, 'error': 'Usuário é obrigatório.'})

            if uid:
                try:
                    obj = User.objects.get(id=uid, empresa=empresa)
                except User.DoesNotExist:
                    return JsonResponse({'ok': False, 'error': 'Usuário não encontrado.'})
                # Verifica duplicidade de username (exceto o próprio)
                if User.objects.filter(username=username).exclude(id=uid).exists():
                    return JsonResponse({'ok': False, 'error': 'Nome de usuário já existe.'})
            else:
                # Verifica limite do plano
                if empresa and not empresa.pode_criar_usuario():
                    return JsonResponse({'ok': False, 'error': f'Limite de usuários do plano {empresa.plano} atingido.'})
                if User.objects.filter(username=username).exists():
                    return JsonResponse({'ok': False, 'error': 'Nome de usuário já existe.'})
                obj = User(empresa=empresa)

            nomes = nome.strip().split(' ', 1)
            obj.first_name = nomes[0]
            obj.last_name  = nomes[1] if len(nomes) > 1 else ''
            obj.username   = username
            obj.email      = email
            obj.perfil     = perfil
            obj.is_active  = ativo
            if senha:
                obj.set_password(senha)
            obj.save()
            return JsonResponse({'ok': True, 'id': obj.id})

        if action == 'delete':
            uid = data.get('id')
            if uid == request.user.id:
                return JsonResponse({'ok': False, 'error': 'Não é possível excluir seu próprio usuário.'})
            try:
                obj = User.objects.get(id=uid, empresa=empresa)
                obj.is_active = False
                obj.save()
                return JsonResponse({'ok': True})
            except User.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Usuário não encontrado.'})

        if action == 'list':
            qs = User.objects.filter(empresa=empresa).order_by('first_name', 'username')
            rows = [{
                'id': u.id,
                'nome': u.get_full_name() or u.username,
                'username': u.username,
                'email': u.email or '—',
                'perfil': u.get_perfil_display(),
                'perfil_val': u.perfil,
                'ativo': u.is_active,
            } for u in qs]
            return JsonResponse({'ok': True, 'rows': rows})

    plano_info = None
    if empresa and empresa.plano:
        total = User.objects.filter(empresa=empresa, is_active=True).count()
        limite = empresa.plano.limite_usuarios
        plano_info = {
            'nome': str(empresa.plano),
            'limite': limite,
            'total': total,
            'restante': (limite - total) if limite > 0 else None,
        }

    return render(request, 'accounts/usuarios.html', {'plano_info': plano_info})
