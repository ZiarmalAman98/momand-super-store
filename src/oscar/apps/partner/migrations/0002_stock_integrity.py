from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models
from django.db.models import Q


def copy_legacy_price(apps, schema_editor):
    StockRecord = apps.get_model("partner", "StockRecord")
    for record in StockRecord.objects.all().iterator():
        legacy = record.price_retail
        if legacy is None:
            legacy = record.price_excl_tax
        if legacy is not None:
            record.price = legacy
            record.save(update_fields=["price"])


class Migration(migrations.Migration):

    dependencies = [
        ("partner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockrecord",
            name="price",
            field=models.DecimalField(
                "Price",
                max_digits=12,
                decimal_places=2,
                blank=True,
                null=True,
                validators=[MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.RunPython(copy_legacy_price, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="stockrecord",
            name="price_excl_tax",
        ),
        migrations.RemoveField(
            model_name="stockrecord",
            name="price_retail",
        ),
        migrations.RemoveField(
            model_name="stockrecord",
            name="cost_price",
        ),
        migrations.AlterField(
            model_name="stockrecord",
            name="num_allocated",
            field=models.IntegerField(
                "Number allocated",
                blank=True,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddIndex(
            model_name="stockrecord",
            index=models.Index(
                fields=["product", "partner"],
                name="partner_stock_product_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockrecord",
            index=models.Index(
                fields=["partner", "date_updated"],
                name="partner_stock_updated_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockrecord",
            constraint=models.CheckConstraint(
                condition=Q(num_allocated__gte=0) | Q(num_allocated__isnull=True),
                name="oscar_stock_allocated_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockrecord",
            constraint=models.CheckConstraint(
                condition=Q(price__gte=0) | Q(price__isnull=True),
                name="oscar_stock_price_nonnegative",
            ),
        ),
    ]
