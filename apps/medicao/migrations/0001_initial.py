from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cadastros", "0001_initial"),
        ("projetos", "0001_initial"),
        ("servicos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BoletimMedicao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=300, verbose_name="Nome / Identificação do BM")),
                ("contrato", models.CharField(blank=True, max_length=200, verbose_name="Contrato")),
                ("codigo_obra", models.CharField(blank=True, max_length=100, verbose_name="Código de Obra")),
                ("logo_bk_nome", models.CharField(blank=True, max_length=200)),
                ("logo_bk_tipo", models.CharField(blank=True, max_length=100)),
                ("logo_bk_dados", models.BinaryField(blank=True, null=True)),
                ("logo_cliente_nome", models.CharField(blank=True, max_length=200)),
                ("logo_cliente_tipo", models.CharField(blank=True, max_length=100)),
                ("logo_cliente_dados", models.BinaryField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="cadastros.cliente",
                        verbose_name="Cliente",
                    ),
                ),
                (
                    "projeto",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="boletins_medicao",
                        to="projetos.projeto",
                        verbose_name="Projeto",
                    ),
                ),
            ],
            options={
                "verbose_name": "Boletim de Medição",
                "verbose_name_plural": "Boletins de Medição",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ItemContrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(blank=True, max_length=100, verbose_name="Código")),
                ("descricao", models.CharField(max_length=500, verbose_name="Descrição")),
                ("quantidade_total", models.DecimalField(decimal_places=3, default=1, max_digits=14, verbose_name="Qtde Total")),
                ("unidade", models.CharField(default="un", max_length=30, verbose_name="Unidade")),
                ("preco_unitario", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Preço Unitário")),
                ("ordem", models.PositiveIntegerField(default=0)),
                (
                    "boletim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens",
                        to="medicao.boletimmedicao",
                        verbose_name="Boletim",
                    ),
                ),
                (
                    "servico",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="servicos.produtoservico",
                        verbose_name="Serviço/Atividade",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item do Contrato",
                "verbose_name_plural": "Itens do Contrato",
                "ordering": ["ordem", "id"],
            },
        ),
        migrations.CreateModel(
            name="PeriodoMedicao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveIntegerField(verbose_name="Número BM")),
                ("data_inicio", models.DateField(verbose_name="Data Início")),
                ("data_fim", models.DateField(verbose_name="Data Fim")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "boletim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periodos",
                        to="medicao.boletimmedicao",
                        verbose_name="Boletim",
                    ),
                ),
            ],
            options={
                "verbose_name": "Período de Medição",
                "verbose_name_plural": "Períodos de Medição",
                "ordering": ["numero"],
                "unique_together": {("boletim", "numero")},
            },
        ),
        migrations.CreateModel(
            name="MedicaoItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantidade_medida", models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name="Quantidade Medida")),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medicoes",
                        to="medicao.itemcontrato",
                        verbose_name="Item",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medicoes",
                        to="medicao.PeriodoMedicao",
                        verbose_name="Período",
                    ),
                ),
            ],
            options={
                "verbose_name": "Medição do Item",
                "verbose_name_plural": "Medições dos Itens",
                "unique_together": {("periodo", "item")},
            },
        ),
    ]
