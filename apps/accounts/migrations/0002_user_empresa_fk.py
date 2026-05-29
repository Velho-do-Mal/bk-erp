from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        # 1. Remove o CharField antigo
        migrations.RemoveField(model_name='user', name='empresa'),

        # 2. Adiciona FK para saas.Empresa
        migrations.AddField(
            model_name='user',
            name='empresa',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='usuarios',
                to='saas.empresa',
                verbose_name='Empresa',
            ),
        ),

        # 3. Adiciona perfil superadmin
        migrations.AlterField(
            model_name='user',
            name='perfil',
            field=models.CharField(
                choices=[('admin','Administrador'),('cliente','Cliente'),('superadmin','Super Admin')],
                default='cliente', max_length=20,
            ),
        ),
    ]
