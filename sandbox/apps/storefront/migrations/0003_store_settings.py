from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("storefront", "0002_contactmessage_phone")]

    operations = [
        migrations.CreateModel(
            name="StoreSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("store_name", models.CharField(default="Momand Super Store", max_length=160)),
                ("tagline", models.CharField(blank=True, max_length=240)),
                ("currency", models.CharField(default="AFN", max_length=3)),
                ("tax_rate", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=6)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.TextField(blank=True)),
                ("payment_methods", models.JSONField(default=list)),
                ("bank_transfer_instructions", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "store settings",
                "verbose_name_plural": "store settings",
            },
        ),
    ]
