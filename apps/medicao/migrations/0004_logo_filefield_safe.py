from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    """
    Garante que as colunas logo_bk e logo_cliente existam na tabela medicao_boletimmedicao.
    Usa ADD COLUMN IF NOT EXISTS (PostgreSQL) para ser idempotente — seguro mesmo que
    0003 já tenha rodado parcialmente ou que o estado esteja inconsistente.
    """

    dependencies = [
        ('medicao', '0003_boletimmedicao_empresa_filefield'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE medicao_boletimmedicao
                    ADD COLUMN IF NOT EXISTS logo_bk VARCHAR(100) NULL;
                ALTER TABLE medicao_boletimmedicao
                    ADD COLUMN IF NOT EXISTS logo_cliente VARCHAR(100) NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.AlterField(
                    model_name='boletimmedicao',
                    name='logo_bk',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
                migrations.AlterField(
                    model_name='boletimmedicao',
                    name='logo_cliente',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
            ],
        ),
    ]
