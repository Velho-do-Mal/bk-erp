from django.db import migrations, models
import django.db.models.deletion

try:
    from apps.core.storage import media_upload_to
except Exception:
    def media_upload_to(instance, filename):
        return filename


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0001_initial"),
        ("medicao", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="boletimmedicao",
            name="empresa",
            field=models.ForeignKey(
                to="saas.empresa",
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                blank=True,
                related_name="+",
                verbose_name="Empresa",
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="boletimmedicao",
            name="logo_bk",
            field=models.FileField(
                upload_to=media_upload_to,
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="boletimmedicao",
            name="logo_cliente",
            field=models.FileField(
                upload_to=media_upload_to,
                null=True,
                blank=True,
            ),
        ),
    ]
