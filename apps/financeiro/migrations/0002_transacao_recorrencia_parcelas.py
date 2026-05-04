# Generated manually — adiciona campo recorrencia_parcelas à Transacao

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='recorrencia_parcelas',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='0 = sem limite (até cancelar); >0 = número de repetições a gerar',
            ),
        ),
    ]
