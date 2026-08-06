import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from apps.accounts.decorators import admin_required
from apps.accounts.models import User
from apps.core.modulos import MODULOS, MODULOS_KEYS


@admin_required
def usuarios(request):
    empresa = getattr(request, 'empresa', None)

    # Só é possível marcar, para um usuário "cliente", módulos que a
    # EMPRESA contratou (Empresa.modulos_contratados) — evita que o admin
    # da empresa libere pra um funcionário um módulo que ela não comprou.
    # Superadmin (empresa=None) continua vendo/podendo marcar todos.
    if empresa is not None:
        contratados = set(empresa.modulos_contratados or [])
        modulos_disponiveis = [(c, r) for c, r in MODULOS if c in contratados]
    else:
        modulos_disponiveis = MODULOS
    chaves_disponiveis = {c for c, _ in modulos_disponiveis}

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
            modulos_raw = data.get('modulos_permitidos') or []
            # Só valida/salva módulos para perfil 'cliente' — admin/superadmin
            # sempre têm acesso total (dentro do que a empresa contratou) e
            # não usam essa lista. Além de ser uma chave de módulo válida,
            # também precisa estar entre os módulos que a EMPRESA contratou
            # (chaves_disponiveis) — trava tanto na tela quanto na API.
            modulos = [m for m in modulos_raw if m in MODULOS_KEYS and m in chaves_disponiveis] if perfil == 'cliente' else []

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
            obj.modulos_permitidos = modulos
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
                'modulos_permitidos': u.modulos_permitidos or [],
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

    return render(request, 'accounts/usuarios.html', {'plano_info': plano_info, 'modulos': modulos_disponiveis})
