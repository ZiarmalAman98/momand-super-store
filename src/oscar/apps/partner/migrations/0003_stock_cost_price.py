from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("partner", "0002_stock_integrity"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockrecord",
            name="cost_price",
            field=models.DecimalField(
                "Average cost price",
                max_digits=12,
                decimal_places=2,
                blank=True,
                null=True,
                validators=[MinValueValidator(Decimal("0"))],
            ),
        ),
    ]
