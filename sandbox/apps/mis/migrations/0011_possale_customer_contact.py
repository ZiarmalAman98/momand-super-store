from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mis", "0010_possalecorrectionrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="possale",
            name="customer_name",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="possale",
            name="customer_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
