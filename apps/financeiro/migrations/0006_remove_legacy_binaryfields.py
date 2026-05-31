from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove anexo_dados do estado de migração (state-only, coluna já não existe no DB).
    """

    dependencies = [
        ('financeiro', '0005_anexo_filefield_safe'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='transacao',
                    name='anexo_dados',
                ),
            ],
        ),
    ]
