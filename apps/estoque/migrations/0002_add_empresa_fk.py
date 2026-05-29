from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0001_initial'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialestoque',
            name='empresa',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa', verbose_name='Empresa'),
        ),
    ]
