from django.db import migrations, models
import apps.core.storage


class Migration(migrations.Migration):
    """
    Adiciona FileField sem remover BinaryField.
    Dados antigos (arquivo_dados) permanecem intactos.
    """
    dependencies = [
        ('documentos', '0003_documento_data_validade'),
    ]

    operations = [
        migrations.AddField(
            model_name='documento',
            name='arquivo',
            field=models.FileField(blank=True, null=True, upload_to=apps.core.storage.media_upload_to),
        ),
    ]
