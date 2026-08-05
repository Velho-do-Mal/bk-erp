from django.db import migrations, models


def preencher_modulos_existentes(apps, schema_editor):
    """
    Preserva o comportamento atual para quem já usa o sistema: usuários
    não-admin existentes recebem todos os módulos liberados (igual ao
    que já viam hoje, quando não havia restrição nenhuma). A partir de
    agora, o administrador pode restringir cada um pela tela de Usuários.
    """
    from apps.core.modulos import MODULOS_KEYS

    User = apps.get_model('accounts', 'User')
    User.objects.filter(perfil='cliente').update(modulos_permitidos=list(MODULOS_KEYS))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_associar_usuarios_bk'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='modulos_permitidos',
            field=models.JSONField(blank=True, default=list, verbose_name='Módulos Permitidos', help_text='Módulos do sistema que este usuário pode acessar (ignorado para administradores, que sempre têm acesso total).'),
        ),
        migrations.RunPython(preencher_modulos_existentes, migrations.RunPython.noop),
    ]
