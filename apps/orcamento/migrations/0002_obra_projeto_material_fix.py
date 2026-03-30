from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orcamento', '0001_initial'),
        ('projetos', '0002_alter_controledocconfig_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='materialcadastro',
            name='codigo_cliente',
            field=models.CharField(blank=True, max_length=255, verbose_name='Codigo Cliente'),
        ),
        migrations.AlterField(
            model_name='materialcadastro',
            name='codigo_bk',
            field=models.CharField(blank=True, max_length=255, verbose_name='Codigo BK'),
        ),
        migrations.AlterField(
            model_name='materialcadastro',
            name='descricao',
            field=models.CharField(max_length=1000, verbose_name='Descricao'),
        ),
        migrations.AlterField(
            model_name='materialcadastro',
            name='unidade',
            field=models.CharField(default='un', max_length=50, verbose_name='Unidade'),
        ),
        migrations.AddField(
            model_name='obra',
            name='projeto',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='obras_orcamento',
                to='projetos.projeto',
                verbose_name='Projeto',
            ),
        ),
    ]
