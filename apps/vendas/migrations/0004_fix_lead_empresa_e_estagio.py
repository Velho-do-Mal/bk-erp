"""
Corrige o model Lead:

1. A migration 0003 adicionou uma coluna FK "empresa_id" para isolamento
   por tenant, mas o código-fonte (apps/vendas/models.py) já tinha um
   CharField também chamado "empresa" — em Python, essa segunda atribuição
   sobrescrevia a primeira no namespace da classe, então o ForeignKey
   NUNCA existiu de fato no model em tempo de execução (confirmado via
   Lead._meta.get_field('empresa') -> CharField). A coluna "empresa_id"
   ficou órfã no banco, nunca populada pela aplicação — removida aqui.
2. A coluna de texto real (razão social do prospect) é renomeada de
   "empresa" para "empresa_nome", liberando o nome "empresa" para o FK
   de tenant de verdade, que passa a funcionar corretamente.
3. Adiciona atualizado_em (usado pelo lembrete automático de "leads sem
   contato há N dias").
4. Unifica ESTAGIO_CHOICES com o que a tela/JS já usam de fato (o model
   tinha uma lista de 4 estágios divergente da migration original e do
   template, que usam 6).
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0003_add_empresa_fk'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        # ORDEM IMPORTA: renomeia a coluna de texto real ANTES de remover o
        # FK órfão. O SQLite reconstrói a tabela inteira ao remover um campo
        # indexado (RemoveField abaixo) preservando só as colunas que já
        # estão no estado do Django naquele momento — se a coluna de texto
        # ainda não tivesse sido registrada no estado (via este RunSQL +
        # state_operations), a reconstrução a perderia silenciosamente.
        migrations.RunSQL(
            sql='ALTER TABLE vendas_lead RENAME COLUMN empresa TO empresa_nome;',
            reverse_sql='ALTER TABLE vendas_lead RENAME COLUMN empresa_nome TO empresa;',
            state_operations=[
                migrations.AddField(
                    model_name='lead',
                    name='empresa_nome',
                    field=models.CharField(blank=True, max_length=200, verbose_name='Empresa (razão social do prospect)'),
                ),
            ],
        ),
        # Remove o FK órfão (empresa_id) — nunca foi populado pela aplicação.
        migrations.RemoveField(model_name='lead', name='empresa'),
        migrations.AddField(
            model_name='lead',
            name='empresa',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa', verbose_name='Empresa'),
        ),
        migrations.AddField(
            model_name='lead',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='lead',
            name='estagio',
            field=models.CharField(
                choices=[
                    ('prospeccao', 'Prospecção'),
                    ('qualificacao', 'Qualificação'),
                    ('proposta', 'Proposta Enviada'),
                    ('negociacao', 'Negociação'),
                    ('fechado_ganho', 'Fechado Ganho'),
                    ('fechado_perdido', 'Fechado Perdido'),
                ],
                default='prospeccao',
                max_length=20,
            ),
        ),
    ]
