from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ProdutoServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(blank=True, max_length=100)),
                ('tipo', models.CharField(
                    choices=[('servico', 'Serviço'), ('produto', 'Produto'), ('ambos', 'Ambos')],
                    default='servico', max_length=10)),
                ('nome', models.CharField(max_length=300)),
                ('descricao', models.TextField(blank=True)),
                ('unidade', models.CharField(blank=True, default='un', max_length=30)),
                ('preco_unitario', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Produto/Serviço',
                'verbose_name_plural': 'Produtos/Serviços',
                'ordering': ['nome'],
            },
        ),
    ]
