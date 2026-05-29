from django.db import migrations
import datetime


def criar_dados_iniciais(apps, schema_editor):
    Plano = apps.get_model('saas', 'Plano')
    Empresa = apps.get_model('saas', 'Empresa')
    Assinatura = apps.get_model('saas', 'Assinatura')

    plano_enterprise = Plano.objects.create(
        nome='enterprise', descricao='Sem limites. Suporte dedicado.',
        preco_mensal=0, limite_usuarios=0, limite_projetos=0, limite_propostas=0
    )
    Plano.objects.create(
        nome='free', descricao='1 usuário, 1 projeto, 5 propostas.',
        preco_mensal=0, limite_usuarios=1, limite_projetos=1, limite_propostas=5
    )
    Plano.objects.create(
        nome='basic', descricao='5 usuários, 10 projetos, 30 propostas.',
        preco_mensal=99, limite_usuarios=5, limite_projetos=10, limite_propostas=30
    )
    Plano.objects.create(
        nome='pro', descricao='20 usuários, 50 projetos, propostas ilimitadas.',
        preco_mensal=299, limite_usuarios=20, limite_projetos=50, limite_propostas=0
    )

    empresa_bk = Empresa.objects.create(
        id=1, nome='BK Engenharia e Tecnologia',
        cnpj='', email='', plano=plano_enterprise, ativa=True
    )
    hoje = datetime.date.today()
    Assinatura.objects.create(
        empresa=empresa_bk, plano=plano_enterprise,
        status='ativa', inicio=hoje,
        vencimento=datetime.date(2099, 12, 31)
    )


def reverter(apps, schema_editor):
    Plano = apps.get_model('saas', 'Plano')
    Empresa = apps.get_model('saas', 'Empresa')
    Empresa.objects.filter(id=1).delete()
    Plano.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('saas', '0001_initial')]
    operations = [migrations.RunPython(criar_dados_iniciais, reverter)]
