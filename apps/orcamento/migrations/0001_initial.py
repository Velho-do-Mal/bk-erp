from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("cadastros", "0001_initial"),
        ("servicos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialCadastro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_cliente", models.CharField(blank=True, max_length=100, verbose_name="Código Cliente")),
                ("codigo_bk", models.CharField(blank=True, max_length=100, verbose_name="Código BK")),
                ("descricao", models.CharField(max_length=500, verbose_name="Descrição")),
                ("unidade", models.CharField(default="un", max_length=30, verbose_name="Unidade")),
                ("valor_unitario", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Valor Unitário")),
                ("ativo", models.BooleanField(default=True, verbose_name="Ativo")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Material",
                "verbose_name_plural": "Materiais",
                "ordering": ["descricao"],
            },
        ),
        migrations.CreateModel(
            name="Obra",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=300, verbose_name="Nome da Obra")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="cadastros.cliente",
                        verbose_name="Cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Obra",
                "verbose_name_plural": "Obras",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="Orcamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(default="Orçamento", max_length=200, verbose_name="Nome")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "obra",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orcamentos",
                        to="orcamento.obra",
                        verbose_name="Obra",
                    ),
                ),
            ],
            options={
                "verbose_name": "Orçamento",
                "verbose_name_plural": "Orçamentos",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ItemMaterial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade", models.DecimalField(decimal_places=3, default=1, max_digits=14, verbose_name="Quantidade")),
                ("valor_unitario", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Valor Unitário")),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="orcamento.materialcadastro",
                        verbose_name="Material",
                    ),
                ),
                (
                    "orcamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens_material",
                        to="orcamento.orcamento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de Material",
                "verbose_name_plural": "Itens de Material",
            },
        ),
        migrations.CreateModel(
            name="ItemServico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade", models.DecimalField(decimal_places=3, default=1, max_digits=14, verbose_name="Quantidade")),
                ("valor_unitario", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Valor Unitário")),
                (
                    "orcamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens_servico",
                        to="orcamento.orcamento",
                    ),
                ),
                (
                    "servico",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="servicos.produtoservico",
                        verbose_name="Serviço",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de Serviço",
                "verbose_name_plural": "Itens de Serviço",
            },
        ),
    ]
