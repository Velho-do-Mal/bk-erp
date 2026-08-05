from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0003_pedidocompra_centro_custo_entregue'),
    ]

    operations = [
        migrations.AddField(
            model_name='itempedidocompra',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('material', '📦 Material'),
                    ('equipamento', '🔧 Equipamento'),
                    ('veiculo', '🚗 Veículo'),
                    ('software', '💻 Software'),
                    ('outro', '📁 Outro'),
                ],
                default='material',
                max_length=15,
            ),
        ),
    ]
