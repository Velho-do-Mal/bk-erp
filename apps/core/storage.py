"""
storage.py — Backend condicional: S3 (prod) ou local (dev).
Ativa S3 quando USE_S3=True nas variáveis de ambiente.
"""
import os
from django.conf import settings


def get_upload_storage():
    """Retorna o backend de storage configurado."""
    if getattr(settings, 'USE_S3', False):
        from storages.backends.s3boto3 import S3Boto3Storage
        return S3Boto3Storage()
    return None  # usa DEFAULT_FILE_STORAGE (local)


def media_upload_to(instance, filename):
    """Gera caminho de upload baseado no modelo."""
    model_name = instance.__class__.__name__.lower()
    empresa_id = getattr(instance, 'empresa_id', 'shared') or 'shared'
    return f'uploads/{empresa_id}/{model_name}/{filename}'
