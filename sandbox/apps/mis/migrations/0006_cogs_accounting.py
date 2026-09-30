from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mis", "0005_split_payment"),
        ("partner", "0008_merge_stock_integrity_partneraddress"),
    ]

    operations = [
        migrations.AddField(
            model_name="possaleitem",
            name="unit_cost",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                blank=True,
                null=True,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddField(
            model_name="possaleitem",
            name="cost_total",
            field=models.DecimalField(
                max_digits=14,
                decimal_places=2,
                default=Decimal("0.00"),
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddField(
            model_name="possalereturnitem",
            name="unit_cost",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                blank=True,
                null=True,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddField(
            model_name="possalereturnitem",
            name="cost_total",
            field=models.DecimalField(
                max_digits=14,
                decimal_places=2,
                default=Decimal("0.00"),
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.CreateModel(
            name="OnlineOrderCost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[MinValueValidator(1)])),
                ("unit_cost", models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])),
                ("cost_total", models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mis_cost_lines", to="order.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="online_order_costs", to="catalogue.product")),
                ("stockrecord", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="online_order_costs", to="partner.stockrecord")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="onlineordercost",
            index=models.Index(fields=["order", "product"], name="mis_online_order_product_idx"),
        ),
        migrations.AddIndex(
            model_name="onlineordercost",
            index=models.Index(fields=["stockrecord", "created_at"], name="mis_online_cost_stock_created"),
        ),
        migrations.AddConstraint(
            model_name="onlineordercost",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_online_cost_qty_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="onlineordercost",
            constraint=models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0) & models.Q(cost_total__gte=0),
                name="mis_online_cost_amounts_nonnegative",
            ),
        ),
    ]
