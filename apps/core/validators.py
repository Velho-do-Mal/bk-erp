"""
validators.py — Validação segura de uploads de arquivo.
Verifica extensão (whitelist), magic bytes e tamanho máximo.
"""
from django.core.exceptions import ValidationError

# Extensões permitidas
ALLOWED_EXTENSIONS = {
    'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'csv', 'zip', 'rar',
}

# Magic bytes: (offset, bytes_esperados, extensões_associadas)
MAGIC_BYTES = [
    (0, b'%PDF',               {'pdf'}),
    (0, b'\xff\xd8\xff',       {'jpg', 'jpeg'}),
    (0, b'\x89PNG\r\n',        {'png'}),
    (0, b'GIF8',               {'gif'}),
    (0, b'BM',                 {'bmp'}),
    (0, b'RIFF',               {'webp'}),
    (0, b'PK\x03\x04',         {'docx', 'xlsx', 'pptx', 'zip'}),
    (0, b'\xd0\xcf\x11\xe0',   {'doc', 'xls', 'ppt'}),
]

# Tamanho máximo: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024


def validate_upload(file):
    """
    Valida um InMemoryUploadedFile ou TemporaryUploadedFile.
    Levanta ValidationError se o arquivo for inválido.
    """
    if file is None:
        return

    # 1. Extensão
    name = file.name or ''
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'Tipo de arquivo não permitido: .{ext}. '
            f'Permitidos: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        )

    # 2. Tamanho
    if file.size > MAX_FILE_SIZE:
        mb = file.size / (1024 * 1024)
        raise ValidationError(
            f'Arquivo muito grande ({mb:.1f} MB). Máximo permitido: 20 MB.'
        )

    # 3. Magic bytes — lê início do arquivo
    file.seek(0)
    header = file.read(16)
    file.seek(0)

    # Para extensões que têm magic bytes definidos, verifica assinatura
    matched = False
    for offset, magic, exts in MAGIC_BYTES:
        if ext in exts:
            if header[offset:offset + len(magic)] == magic:
                matched = True
                break
    else:
        # Extensão sem magic bytes definido (txt, csv, rar…) — aceita
        matched = True

    if not matched:
        raise ValidationError(
            'O conteúdo do arquivo não corresponde à extensão informada. '
            'Possível arquivo malicioso.'
        )


def validate_upload_view(file, field_label='Arquivo'):
    """
    Versão para uso em views (retorna string de erro ou None).
    """
    try:
        validate_upload(file)
        return None
    except ValidationError as e:
        return f'{field_label}: {e.message}'
