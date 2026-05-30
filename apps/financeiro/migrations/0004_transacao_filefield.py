from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0003_add_empresa_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transacao',
            name='anexo_dados',
        ),
        migrations.AddField(
            model_name='transacao',
            name='anexo_arquivo',
            field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
        ),
    ]
