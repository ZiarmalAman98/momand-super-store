from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("partner", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockrecord",
            name="num_allocated",
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[],
                verbose_name="Number allocated",
            ),
        ),
        migrations.AlterField(
            model_name="stockrecord",
            name="price",
            field=models.DecimalField(
                blank=True,
                null=True,
                decimal_places=2,
                max_digits=12,
                validators=[],
                verbose_name="Price",
            ),
        ),
        migrations.AddIndex(
            model_name="stockrecord",
            index=models.Index(fields=["product", "partner"], name="partner_stock_product_idx"),
        ),
        migrations.AddIndex(
            model_name="stockrecord",
            index=models.Index(fields=["partner", "date_updated"], name="partner_stock_updated_idx"),
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
