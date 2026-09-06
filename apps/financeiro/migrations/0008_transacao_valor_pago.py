from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0007_transacao_colaborador'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='valor_pago',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
    ]
