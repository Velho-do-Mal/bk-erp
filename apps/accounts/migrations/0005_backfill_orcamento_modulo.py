from django.db import migrations


def backfill_orcamento(apps, schema_editor):
    """
    'orcamento' passa a ser um módulo controlável (antes não era filtrado
    por ninguém — todo usuário 'cliente' já acessava /orcamento/ livremente).
    Para não tirar acesso de quem já tinha na prática, adiciona 'orcamento'
    à lista de módulos permitidos de todo usuário 'cliente' existente.
    """
    User = apps.get_model('accounts', 'User')
    for u in User.objects.filter(perfil='cliente'):
        mods = u.modulos_permitidos or []
        if 'orcamento' not in mods:
            u.modulos_permitidos = mods + ['orcamento']
            u.save(update_fields=['modulos_permitidos'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_modulos_permitidos'),
    ]

    operations = [
        migrations.RunPython(backfill_orcamento, reverse_noop),
    ]
