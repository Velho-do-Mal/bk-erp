from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.CreateModel(
            name='Departamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(blank=True)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa')),
            ],
            options={'verbose_name': 'Departamento', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='Cargo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('salario_base', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('descricao', models.TextField(blank=True)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa')),
                ('departamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cargos', to='rh.departamento')),
            ],
            options={'verbose_name': 'Cargo', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='Colaborador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('cpf', models.CharField(blank=True, max_length=14)),
                ('rg', models.CharField(blank=True, max_length=20)),
                ('data_nascimento', models.DateField(blank=True, null=True)),
                ('sexo', models.CharField(blank=True, choices=[('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')], max_length=1)),
                ('estado_civil', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True)),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('endereco', models.CharField(blank=True, max_length=300)),
                ('cep', models.CharField(blank=True, max_length=9)),
                ('cidade', models.CharField(blank=True, max_length=100)),
                ('estado', models.CharField(blank=True, max_length=2)),
                ('matricula', models.CharField(blank=True, max_length=30)),
                ('regime', models.CharField(choices=[('clt','CLT'),('pj','PJ'),('estagio','Estágio'),('autonomo','Autônomo'),('temporario','Temporário')], default='clt', max_length=20)),
                ('data_admissao', models.DateField(blank=True, null=True)),
                ('data_demissao', models.DateField(blank=True, null=True)),
                ('salario', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('ativo','Ativo'),('afastado','Afastado'),('ferias','Em Férias'),('desligado','Desligado')], default='ativo', max_length=20)),
                ('banco', models.CharField(blank=True, max_length=100)),
                ('agencia', models.CharField(blank=True, max_length=20)),
                ('conta', models.CharField(blank=True, max_length=30)),
                ('pix', models.CharField(blank=True, max_length=100)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa')),
                ('cargo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='colaboradores', to='rh.cargo')),
                ('departamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='colaboradores', to='rh.departamento')),
            ],
            options={'verbose_name': 'Colaborador', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='Ferias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateField()),
                ('data_fim', models.DateField()),
                ('dias', models.IntegerField(default=30)),
                ('status', models.CharField(choices=[('agendada','Agendada'),('aprovada','Aprovada'),('em_gozo','Em Gozo'),('concluida','Concluída'),('cancelada','Cancelada')], default='agendada', max_length=20)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa')),
                ('colaborador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ferias', to='rh.colaborador')),
            ],
            options={'verbose_name': 'Férias', 'ordering': ['-data_inicio']},
        ),
    ]
