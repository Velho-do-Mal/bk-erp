from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    """Garante coluna anexo_arquivo em financeiro_transacao (idempotente)."""

    dependencies = [
        ('financeiro', '0004_transacao_filefield'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE financeiro_transacao
                    ADD COLUMN IF NOT EXISTS anexo_arquivo VARCHAR(100) NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.AlterField(
                    model_name='transacao',
                    name='anexo_arquivo',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
            ],
        ),
    ]
