from django.shortcuts import redirect
from django.urls import reverse


URLS_PUBLICAS = [
    '/cadastro/',
    '/precos/',
    '/login/',
    '/logout/',
    '/admin/',
]


class TenantMiddleware:
    """
    Injeta request.empresa com base no usuário autenticado.
    - Usuários não autenticados: request.empresa = None
    - Superadmin/superuser: acessa sem restrição (request.empresa = None)
    - Usuários normais: request.empresa = user.empresa
    - Se empresa inativa ou inadimplente: redireciona para /cadastro/?bloqueado=1
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None

        if request.user.is_authenticated:
            # Superadmin tem acesso total sem tenant
            if request.user.is_superuser or getattr(request.user, 'perfil', '') == 'superadmin':
                request.empresa = None
            else:
                empresa = getattr(request.user, 'empresa', None)
                request.empresa = empresa

                # Bloqueia se empresa inativa ou inadimplente
                path = request.path
                eh_publica = any(path.startswith(u) for u in URLS_PUBLICAS)

                if not eh_publica and empresa:
                    if not empresa.ativa:
                        return redirect(reverse('saas:cadastro') + '?bloqueado=inativa')
                    if empresa.inadimplente:
                        return redirect(reverse('saas:cadastro') + '?bloqueado=inadimplente')

        response = self.get_response(request)
        return response
