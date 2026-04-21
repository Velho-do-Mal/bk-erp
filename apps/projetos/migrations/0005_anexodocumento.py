from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0004_projeto_data_conclusao'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnexoDocumento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_original', models.CharField(max_length=300)),
                ('arquivo', models.FileField(upload_to='anexos_controle/')),
                ('tamanho', models.PositiveIntegerField(default=0, help_text='Tamanho em bytes')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('documento', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='anexos',
                    to='projetos.documentocontrole',
                )),
                ('enviado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='anexos_enviados',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Anexo',
                'verbose_name_plural': 'Anexos',
                'ordering': ['criado_em'],
            },
        ),
    ]
