from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Plano',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(choices=[('free','Free'),('basic','Basic'),('pro','Pro'),('enterprise','Enterprise')], max_length=20, unique=True)),
                ('descricao', models.TextField(blank=True)),
                ('preco_mensal', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('limite_usuarios', models.PositiveIntegerField(default=1, help_text='0 = ilimitado')),
                ('limite_projetos', models.PositiveIntegerField(default=1, help_text='0 = ilimitado')),
                ('limite_propostas', models.PositiveIntegerField(default=5, help_text='0 = ilimitado')),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={'verbose_name': 'Plano', 'verbose_name_plural': 'Planos', 'ordering': ['preco_mensal']},
        ),
        migrations.CreateModel(
            name='Empresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('cnpj', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True)),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='logos/')),
                ('ativa', models.BooleanField(default=True)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('plano', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='empresas', to='saas.plano')),
            ],
            options={'verbose_name': 'Empresa', 'verbose_name_plural': 'Empresas', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='Assinatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ativa','Ativa'),('vencida','Vencida'),('cancelada','Cancelada'),('trial','Trial')], default='trial', max_length=20)),
                ('inicio', models.DateField()),
                ('vencimento', models.DateField()),
                ('valor_pago', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('observacao', models.TextField(blank=True)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assinaturas', to='saas.empresa')),
                ('plano', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='saas.plano')),
            ],
            options={'verbose_name': 'Assinatura', 'verbose_name_plural': 'Assinaturas', 'ordering': ['-vencimento']},
        ),
    ]
