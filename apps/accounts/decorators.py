from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse


def admin_required(view_func):
    """
    Decorator que exige perfil admin (ou superuser).
    Em requisições JSON (POST com Content-Type application/json) retorna 403 JSON.
    Em requisições normais redireciona para o dashboard com mensagem.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_admin_erp:
            # Se for requisição AJAX/JSON, retorna JSON
            ct = request.content_type or ''
            if 'application/json' in ct or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Acesso negado. Perfil de administrador necessário.'}, status=403)
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
