"""
A pedido do usuário:

1. Adiciona `temperatura` ao Lead (quente/médio/frio) — combobox de
   prioridade de contato.
2. Simplifica o funil de estágios para o que o usuário efetivamente usa:
   Prospecção -> Proposta Enviada -> Fechamento, mantendo "Perdido" como
   4º estágio (sem ele não haveria como diferenciar um lead esquecido de
   um lead recusado, nem medir taxa de conversão real do funil).
3. Remapeia dados existentes das 6 fases antigas (introduzidas na migration
   0004) para as 4 novas, sem perder histórico:
     qualificacao    -> prospeccao
     negociacao      -> proposta
     fechado_ganho   -> fechamento
     fechado_perdido -> perdido
   (prospeccao e proposta já usam a mesma chave e não mudam)
"""
from django.db import migrations, models


REMAP_ESTAGIO = {
    'qualificacao': 'prospeccao',
    'negociacao': 'proposta',
    'fechado_ganho': 'fechamento',
    'fechado_perdido': 'perdido',
}


def remapear_estagios(apps, schema_editor):
    Lead = apps.get_model('vendas', 'Lead')
    for antigo, novo in REMAP_ESTAGIO.items():
        Lead.objects.filter(estagio=antigo).update(estagio=novo)


def remapear_estagios_reverso(apps, schema_editor):
    # Não há mapeamento 1:1 de volta (ex.: "prospeccao" novo pode ter vindo
    # de "qualificacao" ou já ser "prospeccao" antigo) — reversão intencional
    # como no-op, mantendo os dados no estado das 4 fases.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0004_fix_lead_empresa_e_estagio'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='temperatura',
            field=models.CharField(
                choices=[('quente', '🔥 Quente'), ('medio', '🟡 Médio'), ('frio', '🧊 Frio')],
                default='medio',
                max_length=10,
            ),
        ),
        migrations.RunPython(remapear_estagios, remapear_estagios_reverso),
        migrations.AlterField(
            model_name='lead',
            name='estagio',
            field=models.CharField(
                choices=[
                    ('prospeccao', 'Prospecção'),
                    ('proposta', 'Proposta Enviada'),
                    ('fechamento', 'Fechamento (Ganho)'),
                    ('perdido', 'Perdido'),
                ],
                default='prospeccao',
                max_length=20,
            ),
        ),
    ]
