from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0002_add_empresa_fk'),
        ('cadastros', '0002_add_empresa_fk'),
        ('compras', '0003_pedidocompra_centro_custo_entregue'),
    ]

    operations = [
        # FK centro_custo em MaterialEstoque
        migrations.AddField(
            model_name='materialestoque',
            name='centro_custo',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='materiais_estoque',
                to='cadastros.centrosdecusto',
                verbose_name='Centro de Custos',
            ),
        ),
        # FK pedido_origem em MaterialEstoque
        migrations.AddField(
            model_name='materialestoque',
            name='pedido_origem',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='itens_estoque',
                to='compras.pedidocompra',
                verbose_name='Pedido de Origem',
            ),
        ),
    ]
