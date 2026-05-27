# Generated manually — adiciona lead FK, dados_orcamento e projeto_ref_id na Proposta
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposta",
            name="lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="propostas",
                to="vendas.lead",
                verbose_name="Lead",
            ),
        ),
        migrations.AddField(
            model_name="proposta",
            name="dados_orcamento",
            field=models.JSONField(blank=True, default=dict, verbose_name="Dados do Orçamento"),
        ),
        migrations.AddField(
            model_name="proposta",
            name="projeto_ref_id",
            field=models.IntegerField(blank=True, null=True, verbose_name="ID do Projeto Criado"),
        ),
    ]
