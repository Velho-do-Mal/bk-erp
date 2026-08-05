"""
Fonte única de verdade para os módulos do sistema que podem ser
liberados/restringidos por usuário (permissionamento de funcionários).

- `MODULOS`: lista de (chave, rótulo) exibida no cadastro de usuários.
- `MODULOS_KEYS`: apenas as chaves, usado para validar/migrar dados.
- `URL_POR_MODULO`: url name usado para redirecionar o usuário para o
  seu primeiro módulo liberado (quando ele não tem acesso à Home).
- `PREFIXO_URL_POR_MODULO`: primeiro segmento da URL de cada módulo,
  usado pelo middleware de permissão (apps/core/permissoes.py) para
  bloquear acesso direto por link a um módulo não liberado.

Observação: a Home (Dashboard) NÃO é um módulo selecionável — ela é
sempre visível apenas para administradores (perfil admin/superadmin
ou is_superuser). Funcionários sem permissão de Home são
redirecionados automaticamente para o primeiro módulo liberado.
"""

MODULOS = [
    ("projetos", "Gestão de Projetos"),
    ("financeiro", "Financeiro"),
    ("documentos", "Documentos"),
    ("estoque", "Estoque"),
    ("compras", "Compras"),
    ("vendas", "Vendas"),
    ("medicao", "Boletim de Medição"),
    ("rh", "Recursos Humanos"),
    ("relatorios", "Relatórios"),
    ("servicos", "Serviços / Produtos"),
    ("cadastros", "Cadastros (Clientes, Fornecedores, Centros de Custo)"),
]

MODULOS_KEYS = [chave for chave, _ in MODULOS]

URL_POR_MODULO = {
    "projetos": "projetos:lista",
    "financeiro": "financeiro:dashboard",
    "documentos": "documentos:lista",
    "estoque": "estoque:lista",
    "compras": "compras:lista",
    "vendas": "vendas:lista",
    "medicao": "medicao:dashboard",
    "rh": "rh:colaboradores",
    "relatorios": "relatorios:dashboard",
    "servicos": "servicos:lista",
    "cadastros": "cadastros:clientes",
}

# Primeiro segmento da URL -> módulo (usado pelo middleware de permissão).
# Algumas rotas de exportação (ex: /exportar-clientes/) ficam fora desse
# mapeamento; a proteção principal (menu + página) continua valendo.
PREFIXO_URL_POR_MODULO = {
    "projetos": "projetos",
    "financeiro": "financeiro",
    "documentos": "documentos",
    "estoque": "estoque",
    "compras": "compras",
    "vendas": "vendas",
    "medicao": "medicao",
    "rh": "rh",
    "relatorios": "relatorios",
    "servicos": "servicos",
    "cadastros": "cadastros",
}


def primeiro_modulo_url(user):
    """Retorna a URL do primeiro módulo liberado para o usuário, ou None."""
    from django.urls import reverse

    permitidos = set(getattr(user, "modulos_permitidos", None) or [])
    for chave, _ in MODULOS:
        if chave in permitidos and chave in URL_POR_MODULO:
            return reverse(URL_POR_MODULO[chave])
    return None
