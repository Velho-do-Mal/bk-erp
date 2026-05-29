from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0002_proposta_lead_orcamento'),
        ('saas', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposta',
            name='empresa',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa', verbose_name='Empresa'),
        ),
        migrations.AddField(
            model_name='itemproposta',
            name='empresa',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa', verbose_name='Empresa'),
        ),
        migrations.AddField(
            model_name='lead',
            name='empresa',
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='saas.empresa', verbose_name='Empresa'),
        ),
    ]
