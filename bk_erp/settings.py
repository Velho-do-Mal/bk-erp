import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# DEBUG: o padrão (quando a variável de ambiente não está definida) é SEMPRE
# False — o modo verboso deve ser uma escolha explícita do ambiente local
# (.env com DEBUG=True), nunca o comportamento acidental de produção.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# SECRET_KEY: nunca usar uma string fixa como fallback (ficaria exposta a
# qualquer pessoa com acesso ao código-fonte, permitindo forjar sessões,
# tokens CSRF e links de redefinição de senha). Em produção (DEBUG=False)
# a variável é obrigatória. Em desenvolvimento, gera uma chave aleatória
# a cada início de processo (não persiste — suficiente para uso local).
SECRET_KEY = os.environ.get('SECRET_KEY', '').strip()
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError(
            'SECRET_KEY não configurada. Defina a variável de ambiente SECRET_KEY '
            '(ex.: no Railway, em Settings → Variables) antes de rodar em produção.'
        )
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
    warnings.warn(
        'SECRET_KEY não definida — usando chave temporária apenas para desenvolvimento local.',
        RuntimeWarning,
    )

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Duração do período de trial gratuito no autocadastro (/cadastro/).
# Ajustável por variável de ambiente sem precisar de deploy de código.
TRIAL_DIAS = int(os.environ.get('TRIAL_DIAS', '10'))

# Lembretes automáticos por e-mail (management command enviar_alertas,
# executado diariamente pelo cron do Railway — ver railway.toml). Um lead
# ou proposta "parado" pelo número de dias abaixo, sem nenhuma edição,
# entra no e-mail do dia seguinte — editar o registro reseta a contagem.
DIAS_LEMBRAR_LEAD = int(os.environ.get('DIAS_LEMBRAR_LEAD', '3'))
DIAS_LEMBRAR_PROPOSTA = int(os.environ.get('DIAS_LEMBRAR_PROPOSTA', '5'))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',
    'apps.projetos',
    'apps.core',
    'apps.cadastros',
    'apps.financeiro',
    'apps.documentos',
    'apps.estoque',
    'apps.compras',
    'apps.vendas',
    'apps.servicos',
    # NÃO REMOVER 'apps.orcamento' daqui, mesmo que o módulo tenha sido
    # descontinuado (redundante com Vendas, a pedido do usuário) — a
    # migration apps/saas/migrations/0003_associar_dados_bk.py depende
    # explicitamente de 'orcamento' no grafo de migrations. Removê-lo do
    # INSTALLED_APPS quebra "manage.py migrate" para o projeto INTEIRO
    # (NodeNotFoundError), o que quebraria o deploy automático no Railway.
    # O módulo foi desativado para o usuário final removendo suas rotas
    # (bk_erp/urls.py) e sua entrada no menu/permissões
    # (apps/core/modulos.py, templates/base.html) — as URLs /orcamento/...
    # agora retornam 404 e o módulo não aparece em nenhum menu, mas o
    # app continua registrado para não corromper o histórico de migrations.
    'apps.orcamento',
    'apps.medicao',
    'django.contrib.humanize',
    'apps.saas',
    'apps.rh',
    'apps.relatorios',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.saas.middleware.TenantMiddleware',
    'apps.core.permissoes.ModulosPermissionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bk_erp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bk_erp.wsgi.application'

# Banco de dados
import dj_database_url
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL and DATABASE_URL.startswith(('postgres', 'postgresql', 'cockroach', 'mysql', 'sqlite')):
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

AUTH_USER_MODEL = 'accounts.User'

# Upload limits (logos e anexos)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB (JSON body)
FILE_UPLOAD_MAX_MEMORY_SIZE  = 10 * 1024 * 1024   # 10 MB (multipart)

CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://bk-erp-production.up.railway.app'
).split(',')

# ── E-mail (SMTP) ──────────────────────────────────────────────────────────
# Configure as variáveis no Railway:
#   EMAIL_HOST=smtp.gmail.com
#   EMAIL_PORT=587
#   EMAIL_HOST_USER=seu@gmail.com
#   EMAIL_HOST_PASSWORD=sua_senha_de_app
#   DEFAULT_FROM_EMAIL=BK ERP <seu@gmail.com>
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'   # local: imprime no console
)
EMAIL_HOST          = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT          = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS       = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.environ.get('DEFAULT_FROM_EMAIL', 'BK ERP <noreply@bk-engenharia.com>')

# ── Armazenamento de Mídia ─────────────────────────────────────────────────
import os as _os

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

USE_S3 = _os.environ.get('USE_S3', 'False') == 'True'

if USE_S3:
    AWS_ACCESS_KEY_ID = _os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = _os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = _os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
    AWS_S3_REGION_NAME = _os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_VERIFY = True
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# ── Rate Limiting ─────────────────────────────────────────────────────────
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_ENABLE = True
