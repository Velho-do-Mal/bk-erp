from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0003_materialestoque_centro_custo_pedido_origem'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialestoque',
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
