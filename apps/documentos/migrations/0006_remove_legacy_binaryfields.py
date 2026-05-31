from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove arquivo_dados do estado de migração (state-only, coluna já não existe no DB).
    """

    dependencies = [
        ('documentos', '0005_arquivo_filefield_safe'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='documento',
                    name='arquivo_dados',
                ),
            ],
        ),
    ]
