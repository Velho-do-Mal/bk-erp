"""
A pedido do usuário: no combobox de "favorecido" da Transação, junto
com Fornecedores devem aparecer também Colaboradores (ex.: reembolso,
vale, adiantamento pago a um funcionário). Adiciona FK opcional
`colaborador`, mutuamente exclusiva com `fornecedor` por lançamento.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0006_remove_legacy_binaryfields'),
        ('rh', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='colaborador',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transacoes', to='rh.colaborador',
            ),
        ),
    ]
