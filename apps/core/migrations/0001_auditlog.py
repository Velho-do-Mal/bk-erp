from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0003_associar_usuarios_bk'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('acao', models.CharField(choices=[('criar','Criou'),('editar','Editou'),('excluir','Excluiu'),('login','Login'),('logout','Logout'),('exportar','Exportou')], max_length=20)),
                ('modelo', models.CharField(max_length=100)),
                ('objeto_id', models.CharField(blank=True, max_length=50)),
                ('detalhe', models.TextField(blank=True)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.user')),
                ('empresa', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='saas.empresa')),
            ],
            options={'verbose_name': 'Log de Auditoria', 'verbose_name_plural': 'Logs de Auditoria', 'ordering': ['-criado_em']},
        ),
    ]
