from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0002_add_empresa_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='documento',
            name='data_validade',
            field=models.DateField(blank=True, null=True, verbose_name='Data de Validade',
                                   help_text='Deixe em branco se o documento não vence'),
        ),
    ]
