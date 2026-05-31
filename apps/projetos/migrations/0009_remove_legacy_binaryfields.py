from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove logo_bk_dados e logo_cliente_dados do ConfiguracaoProjeto (state-only).
    """

    dependencies = [
        ('projetos', '0008_logo_filefield_safe'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='configuracaoprojeto',
                    name='logo_bk_dados',
                ),
                migrations.RemoveField(
                    model_name='configuracaoprojeto',
                    name='logo_cliente_dados',
                ),
            ],
        ),
    ]
