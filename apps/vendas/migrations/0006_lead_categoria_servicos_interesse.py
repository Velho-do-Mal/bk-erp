"""
A pedido do usuário: adiciona dois campos ao Lead:

1. categoria — combobox fixo (Transmissora, Distribuidora, Empreiteira,
   Construtora, Eólica, EPC, Industrial, Engenharia), para segmentar o
   pipeline por tipo de cliente/mercado.
2. servicos_interesse — texto livre, para registrar quais serviços da BK
   o prospect demonstrou interesse.

Ambos opcionais (blank=True) para não quebrar leads já cadastrados.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0005_lead_temperatura_e_estagio_3_fases'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='categoria',
            field=models.CharField(
                blank=True,
                choices=[
                    ('transmissora', 'Transmissora'),
                    ('distribuidora', 'Distribuidora'),
                    ('empreiteira', 'Empreiteira'),
                    ('construtora', 'Construtora'),
                    ('eolica', 'Eólica'),
                    ('epc', 'EPC'),
                    ('industrial', 'Industrial'),
                    ('engenharia', 'Engenharia'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='lead',
            name='servicos_interesse',
            field=models.TextField(blank=True, verbose_name='Serviços de Interesse'),
        ),
    ]
