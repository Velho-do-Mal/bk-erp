from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    """Garante colunas logo_bk e logo_cliente em projetos_controledocconfig (idempotente)."""

    dependencies = [
        ('projetos', '0007_projeto_filefield'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE projetos_controledocconfig
                    ADD COLUMN IF NOT EXISTS logo_bk VARCHAR(100) NULL;
                ALTER TABLE projetos_controledocconfig
                    ADD COLUMN IF NOT EXISTS logo_cliente VARCHAR(100) NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.AlterField(
                    model_name='controledocconfig',
                    name='logo_bk',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
                migrations.AlterField(
                    model_name='controledocconfig',
                    name='logo_cliente',
                    field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
                ),
            ],
        ),
    ]
