"""
Migration 0004 — Refatoração do módulo Orçamento
=================================================
1. Apaga TODOS os registros de ItemMaterial e MaterialCadastro
2. Remove a coluna material (FK → MaterialCadastro) de ItemMaterial
3. Adiciona a coluna produto (FK → ProdutoServico) em ItemMaterial
4. Remove a tabela MaterialCadastro
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orcamento", "0003_alter_materialcadastro_codigo_bk_and_more"),
        ("servicos", "0001_initial"),
    ]

    operations = [
        # 1. Apaga todos os itens de material existentes (referenciavam MaterialCadastro)
        migrations.RunSQL(
            sql="DELETE FROM orcamento_itemmaterial;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 2. Apaga todos os materiais cadastrados (tabela própria que será removida)
        migrations.RunSQL(
            sql="DELETE FROM orcamento_materialcadastro;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 3. Remove a FK antiga (material → MaterialCadastro)
        migrations.RemoveField(
            model_name="itemmaterial",
            name="material",
        ),
        # 4. Adiciona FK nova (produto → ProdutoServico)
        migrations.AddField(
            model_name="itemmaterial",
            name="produto",
            field=models.ForeignKey(
                default=1,  # temporário — tabela está vazia após o DELETE
                on_delete=django.db.models.deletion.PROTECT,
                to="servicos.produtoservico",
                verbose_name="Produto/Material",
            ),
            preserve_default=False,
        ),
        # 5. Remove a tabela MaterialCadastro
        migrations.DeleteModel(
            name="MaterialCadastro",
        ),
    ]
