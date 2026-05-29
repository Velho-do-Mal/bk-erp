from django.db import migrations


def associar_bk(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Empresa = apps.get_model('saas', 'Empresa')
    try:
        bk = Empresa.objects.get(id=1)
        User.objects.filter(empresa__isnull=True).update(empresa=bk)
    except Empresa.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_user_empresa_fk')]
    operations = [migrations.RunPython(associar_bk, migrations.RunPython.noop)]
