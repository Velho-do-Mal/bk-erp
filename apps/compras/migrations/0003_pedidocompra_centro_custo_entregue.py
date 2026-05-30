from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0002_add_empresa_fk'),
        ('cadastros', '0002_add_empresa_fk'),
    ]

    operations = [
        # Adicionar FK centro_custo em PedidoCompra
        migrations.AddField(
            model_name='pedidocompra',
            name='centro_custo',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pedidos_compra',
                to='cadastros.centrosdecusto',
                verbose_name='Centro de Custos',
            ),
        ),
        # Adicionar status 'entregue'
        migrations.AlterField(
            model_name='pedidocompra',
            name='status',
            field=models.CharField(
                choices=[
                    ('aberta', 'Aberta'),
                    ('aprovacao', 'Aguardando Aprovação'),
                    ('aprovada', 'Aprovada'),
                    ('entregue', 'Entregue'),
                    ('recebida', 'Recebida'),
                    ('encerrada', 'Encerrada'),
                    ('cancelada', 'Cancelada'),
                ],
                default='aberta',
                max_length=15,
            ),
        ),
    ]
