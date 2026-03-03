from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Projeto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=300)),
                ('status', models.CharField(
                    choices=[('rascunho','Rascunho'),('planejamento','Planejamento'),
                             ('execucao','Em Execução'),('revisao','Em Revisão'),
                             ('concluido','Concluído'),('cancelado','Cancelado')],
                    default='rascunho', max_length=30)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('gerente', models.CharField(blank=True, max_length=200)),
                ('patrocinador', models.CharField(blank=True, max_length=200)),
                ('encerrado', models.BooleanField(default=False)),
                ('dados', models.JSONField(default=dict)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Projeto', 'verbose_name_plural': 'Projetos', 'ordering': ['-criado_em']},
        ),
        migrations.CreateModel(
            name='ProjetoAcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='acessos', to='projetos.projeto')),
                ('usuario', models.CharField(max_length=150)),
                ('pode_ver_tap', models.BooleanField(default=True)),
                ('pode_ver_eap', models.BooleanField(default=True)),
                ('pode_ver_gantt', models.BooleanField(default=True)),
                ('pode_ver_controle', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ControleDocConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('projeto', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name='controle_config', to='projetos.projeto')),
                ('cliente_nome', models.CharField(blank=True, max_length=200)),
                ('projeto_numero', models.CharField(blank=True, max_length=100)),
                ('projeto_status', models.CharField(blank=True, max_length=100)),
                ('logo_bk_nome', models.CharField(blank=True, max_length=200)),
                ('logo_bk_tipo', models.CharField(blank=True, max_length=100)),
                ('logo_bk_dados', models.BinaryField(blank=True, null=True)),
                ('logo_cliente_nome', models.CharField(blank=True, max_length=200)),
                ('logo_cliente_tipo', models.CharField(blank=True, max_length=100)),
                ('logo_cliente_dados', models.BinaryField(blank=True, null=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='DocumentoControle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='documentos_controle', to='projetos.projeto')),
                ('servico_nome', models.CharField(blank=True, max_length=200)),
                ('doc_nome', models.CharField(blank=True, max_length=300)),
                ('doc_numero', models.CharField(blank=True, max_length=100)),
                ('revisao', models.CharField(blank=True, default='R0A', max_length=20)),
                ('responsavel_bk', models.CharField(blank=True, max_length=200)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_conclusao', models.DateField(blank=True, null=True)),
                ('percentual_concluido', models.IntegerField(default=0)),
                ('status', models.CharField(
                    choices=[('nao_iniciado','Não Iniciado'),('em_andamento','Em Andamento'),
                             ('em_analise','Em Análise'),('em_revisao','Em Revisão'),
                             ('concluido','Concluído'),('cancelado','Cancelado')],
                    default='nao_iniciado', max_length=20)),
                ('observacao', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='StatusEventoDocumento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('documento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='eventos', to='projetos.documentocontrole')),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    to='projetos.projeto')),
                ('data_evento', models.DateField()),
                ('status', models.CharField(max_length=20)),
                ('responsavel', models.CharField(default='BK', max_length=10)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['data_evento', 'id']},
        ),
    ]
