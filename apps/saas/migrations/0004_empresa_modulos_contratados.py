from django.db import migrations, models
import apps.saas.models


class Migration(migrations.Migration):

    dependencies = [
        ('saas', '0003_associar_dados_bk'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='modulos_contratados',
            field=models.JSONField(
                blank=True,
                default=apps.saas.models._todos_modulos,
                help_text=(
                    'Módulos do sistema que esta empresa contratou. Vale para TODOS os '
                    'usuários dela, inclusive administradores — se um módulo não está '
                    'aqui, ninguém da empresa o acessa. Editável no cadastro da Empresa.'
                ),
                verbose_name='Módulos Contratados',
            ),
        ),
    ]
