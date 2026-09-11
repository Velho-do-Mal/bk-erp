from django.db import migrations, models


class Migration(migrations.Migration):
    """Adiciona 'em_aprovacao' às opções válidas de Projeto.status.

    Só altera metadados de choices (validação/rótulo em formulários e
    get_status_display()) — não muda o schema da coluna nem os dados.
    Projetos com esse valor já existiam em produção (criados por um
    fluxo que não passa pelas choices do model), mas apareciam sem
    rótulo/badge correto nas telas por não estarem listados aqui.
    """

    dependencies = [
        ('projetos', '0009_remove_legacy_binaryfields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projeto',
            name='status',
            field=models.CharField(
                choices=[
                    ('rascunho', 'Rascunho'),
                    ('em_aprovacao', 'Em Aprovação'),
                    ('planejamento', 'Planejamento'),
                    ('execucao', 'Execução'),
                    ('monitoramento', 'Monitoramento'),
                    ('encerrado', 'Encerrado'),
                    ('suspenso', 'Suspenso'),
                ],
                default='rascunho',
                max_length=30,
            ),
        ),
    ]
