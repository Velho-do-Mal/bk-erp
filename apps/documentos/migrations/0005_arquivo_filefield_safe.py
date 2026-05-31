from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    """Garante coluna arquivo em documentos_documento (idempotente)."""

    dependencies = [
        ('documentos', '0004_documento_filefield'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE documentos_documento
                    ADD COLUMN IF NOT EXISTS arquivo VARCHAR(100) NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.AlterField(
                    model_name='documento',
                    name='arquivo',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
            ],
        ),
    ]
