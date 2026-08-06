from django.shortcuts import redirect

from apps.core.modulos import PREFIXO_URL_POR_MODULO


class ModulosPermissionMiddleware:
    """
    Bloqueia acesso direto (por URL) a módulos que o usuário não tem
    permissão de utilizar — complementa a ocultação dos links no menu
    lateral (templates/base.html), que sozinha não impede o acesso via
    link direto/favorito.

    Apenas o superadmin da plataforma (is_superadmin) nunca é bloqueado
    aqui — administradores de empresa continuam sujeitos ao que a
    empresa contratou (ver User.tem_modulo). Usuários não autenticados
    também não são afetados aqui (o @login_required de cada view
    continua sendo a primeira barreira).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not user.is_superadmin:
            primeiro_segmento = request.path.strip('/').split('/', 1)[0]
            modulo = PREFIXO_URL_POR_MODULO.get(primeiro_segmento)

            if modulo and not user.tem_modulo(modulo):
                return redirect('core:dashboard')

        return self.get_response(request)
