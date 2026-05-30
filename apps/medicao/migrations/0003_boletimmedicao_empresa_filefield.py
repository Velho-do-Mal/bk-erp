from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    dependencies = [
        ('medicao', '0002_add_empresa_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='boletimmedicao',
            name='logo_bk',
            field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
        ),
        migrations.AddField(
            model_name='boletimmedicao',
            name='logo_cliente',
            field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
        ),
    ]
