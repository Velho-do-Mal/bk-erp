from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove logo_bk_dados e logo_cliente_dados do estado de migração.
    As colunas já foram deletadas do DB em commit anterior (6fbd6d0).
    Esta migration é state-only: não executa nenhum SQL.
    """

    dependencies = [
        ('medicao', '0004_logo_filefield_safe'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # colunas já não existem no DB
            state_operations=[
                migrations.RemoveField(
                    model_name='boletimmedicao',
                    name='logo_bk_dados',
                ),
                migrations.RemoveField(
                    model_name='boletimmedicao',
                    name='logo_cliente_dados',
                ),
            ],
        ),
    ]
