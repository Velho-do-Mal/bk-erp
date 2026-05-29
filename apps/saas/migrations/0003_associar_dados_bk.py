from django.db import migrations


def associar_empresa_bk(apps, schema_editor):
    """Associa todos os registros sem empresa à empresa BK (id=1)."""
    from django.apps import apps as django_apps
    try:
        Empresa = django_apps.get_model('saas', 'Empresa')
        bk = Empresa.objects.get(id=1)
    except Exception:
        return

    app_models = [
        ('cadastros', 'Cliente'),
        ('cadastros', 'Fornecedor'),
        ('cadastros', 'CentrosDeCusto'),
        ('financeiro', 'Conta'),
        ('financeiro', 'Categoria'),
        ('financeiro', 'Transacao'),
        ('financeiro', 'Orcamento'),
        ('compras', 'PedidoCompra'),
        ('estoque', 'MaterialEstoque'),
        ('vendas', 'Proposta'),
        ('vendas', 'Lead'),
        ('documentos', 'Documento'),
        ('servicos', 'ProdutoServico'),
        ('projetos', 'Projeto'),
        ('orcamento', 'Obra'),
        ('orcamento', 'Orcamento'),
        ('medicao', 'BoletimMedicao'),
    ]
    for app_label, model_name in app_models:
        try:
            Model = django_apps.get_model(app_label, model_name)
            Model.objects.filter(empresa__isnull=True).update(empresa=bk)
        except Exception as e:
            print(f"Aviso: {app_label}.{model_name}: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0002_add_empresa_fk'),
        ('financeiro', '0003_add_empresa_fk'),
        ('compras', '0002_add_empresa_fk'),
        ('estoque', '0002_add_empresa_fk'),
        ('vendas', '0003_add_empresa_fk'),
        ('documentos', '0002_add_empresa_fk'),
        ('servicos', '0002_add_empresa_fk'),
        ('projetos', '0006_add_empresa_fk'),
        ('orcamento', '0005_add_empresa_fk'),
        ('medicao', '0002_add_empresa_fk'),
        ('accounts', '0003_associar_usuarios_bk'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.RunPython(associar_empresa_bk, migrations.RunPython.noop),
    ]
