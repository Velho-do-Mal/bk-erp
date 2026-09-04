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
    - Se empresa inativa ou inadimplente: redireciona para /cadastro/?bloqueado=...

    INVARIANTE DE SEGURANÇA (isolamento multi-tenant):
    Em toda a aplicação, os helpers de tenant (`_qs_empresa`,
    `tenant_get_or_404`, `tenant_get_qs` — um por app) tratam
    `request.empresa is None` como "não filtrar por empresa", ou seja,
    como sinônimo de superadmin. Este middleware é o único lugar
    responsável por garantir que essa equivalência é sempre verdadeira.

    Por isso um usuário autenticado que NÃO é superadmin e cuja
    `empresa` veio None (cadastro incompleto feito fora do fluxo normal,
    ou empresa excluída — o FK usa on_delete=SET_NULL) é bloqueado aqui,
    em vez de seguir adiante como se não tivesse restrição nenhuma. Sem
    esse bloqueio, esse usuário veria os dados de TODAS as empresas em
    cada tela do sistema. A primeira camada dessa proteção é a
    constraint de banco em apps.accounts.models.User.Meta.constraints,
    que impede esse estado de existir na maioria dos casos — este
    bloqueio é a segunda camada, para dados legados/exceções que
    antecedem a constraint.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None

        if request.user.is_authenticated:
            eh_superadmin = (
                request.user.is_superuser
                or getattr(request.user, 'perfil', '') == 'superadmin'
            )

            if eh_superadmin:
                request.empresa = None
            else:
                empresa = getattr(request.user, 'empresa', None)
                path = request.path
                eh_publica = any(path.startswith(u) for u in URLS_PUBLICAS)

                if empresa is None:
                    # Usuário comum sem empresa vinculada: NUNCA deixar passar
                    # como se fosse "sem restrição" (ver docstring da classe).
                    request.empresa = None
                    if not eh_publica:
                        return redirect(reverse('saas:cadastro') + '?bloqueado=sem_empresa')
                else:
                    request.empresa = empresa

                    if not eh_publica:
                        if not empresa.ativa:
                            return redirect(reverse('saas:cadastro') + '?bloqueado=inativa')
                        if empresa.inadimplente:
                            return redirect(reverse('saas:cadastro') + '?bloqueado=inadimplente')

        response = self.get_response(request)
        return response
