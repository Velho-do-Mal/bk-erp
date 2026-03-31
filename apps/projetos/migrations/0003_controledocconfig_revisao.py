from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0002_alter_controledocconfig_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='controledocconfig',
            name='revisao',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
