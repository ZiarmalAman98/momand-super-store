# Generated for the production MIS model alignment.
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mis", "0001_initial"),
        ("catalogue", "0001_initial"),
        ("partner", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="category",
            field=models.CharField(
                choices=[
                    ("electricity", "Electricity"),
                    ("rent", "Rent"),
                    ("salary", "Salary"),
                    ("transportation", "Transportation"),
                    ("internet", "Internet"),
                    ("maintenance", "Maintenance"),
                    ("other", "Other"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="expense",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("card", "Card"),
                    ("bank_transfer", "Bank transfer"),
                    ("other", "Other"),
                ],
                default="cash",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["category", "spent_at"], name="mis_expense_cat_spent_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["payment_method", "spent_at"], name="mis_expense_pay_spent_idx"),
        ),
        migrations.AddField(
            model_name="purchase",
            name="currency",
            field=models.CharField(default="AFN", max_length=12),
        ),
        migrations.AddField(
            model_name="purchase",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("received", "Received")],
                db_index=True,
                default="draft",
                max_length=12,
            ),
        ),
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(fields=["supplier", "purchased_at"], name="mis_purchase_supplier_date_idx"),
        ),
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(fields=["status", "purchased_at"], name="mis_purchase_status_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="purchase",
            constraint=models.CheckConstraint(
                condition=models.Q(total_cost__gte=0),
                name="mis_purchase_total_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="PurchaseItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "line_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mis_purchase_items",
                        to="catalogue.product",
                    ),
                ),
                (
                    "purchase",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="mis.purchase",
                    ),
                ),
                (
                    "stockrecord",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mis_purchase_items",
                        to="partner.stockrecord",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="purchaseitem",
            index=models.Index(fields=["purchase", "product"], name="mis_puritem_purchase_product_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseitem",
            index=models.Index(fields=["stockrecord"], name="mis_puritem_stockrecord_idx"),
        ),
        migrations.AddConstraint(
            model_name="purchaseitem",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_purchase_item_qty_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="purchaseitem",
            constraint=models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="mis_purchase_item_cost_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="purchaseitem",
            constraint=models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="mis_purchase_item_total_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="POSSale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "invoice_number",
                    models.CharField(
                        default=__import__("apps.mis.models", fromlist=["make_pos_invoice_number"]).make_pos_invoice_number,
                        editable=False,
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("currency", models.CharField(max_length=12)),
                (
                    "subtotal",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "discount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "tax",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "total",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("card", "Card"),
                            ("bank_transfer", "Bank transfer"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "amount_tendered",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "change_due",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "cashier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pos_sales",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pos_purchases",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["created_at", "cashier"], name="mis_possale_created_cashier_idx"),
                    models.Index(fields=["created_at", "payment_method"], name="mis_possale_created_payment_idx"),
                    models.Index(fields=["customer", "created_at"], name="mis_possale_customer_created_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="possale",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(subtotal__gte=0)
                    & models.Q(discount__gte=0)
                    & models.Q(tax__gte=0)
                    & models.Q(total__gte=0)
                    & models.Q(amount_tendered__gte=0)
                    & models.Q(change_due__gte=0)
                ),
                name="mis_pos_sale_amounts_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="POSSaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("sku", models.CharField(blank=True, max_length=128)),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                (
                    "unit_price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "unit_tax",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "line_total",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pos_sale_items",
                        to="catalogue.product",
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="mis.possale",
                    ),
                ),
                (
                    "stockrecord",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pos_sale_items",
                        to="partner.stockrecord",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["sale", "product"], name="mis_positem_sale_product_idx"),
                    models.Index(fields=["stockrecord"], name="mis_positem_stockrecord_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="possaleitem",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_pos_sale_item_qty_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="possaleitem",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(unit_price__gte=0)
                    & models.Q(unit_tax__gte=0)
                    & models.Q(line_total__gte=0)
                ),
                name="mis_pos_sale_item_amounts_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="POSSaleReturn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "invoice_number",
                    models.CharField(
                        default=__import__("apps.mis.models", fromlist=["make_pos_return_number"]).make_pos_return_number,
                        editable=False,
                        max_length=32,
                        unique=True,
                    ),
                ),
                (
                    "refund_method",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("card", "Card"),
                            ("bank_transfer", "Bank transfer"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "refund_total",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("reason", models.CharField(max_length=240)),
                ("restocked", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "processed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pos_returns",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="returns",
                        to="mis.possale",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["sale", "created_at"], name="mis_posret_sale_created_idx"),
                    models.Index(fields=["refund_method", "created_at"], name="mis_posret_refund_created_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="possalereturn",
            constraint=models.CheckConstraint(
                condition=models.Q(refund_total__gte=0),
                name="mis_pos_return_total_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="POSSaleReturnItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                (
                    "refund_amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "sale_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="return_items",
                        to="mis.possaleitem",
                    ),
                ),
                (
                    "sale_return",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="mis.possalereturn",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["sale_return", "sale_item"], name="mis_posretitem_return_sale_idx"),
                    models.Index(fields=["sale_item"], name="mis_posretitem_sale_item_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="possalereturnitem",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_pos_return_item_qty_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="possalereturnitem",
            constraint=models.CheckConstraint(
                condition=models.Q(refund_amount__gte=0),
                name="mis_pos_return_item_amount_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("opening", "Opening stock"),
                            ("purchase", "Purchase"),
                            ("pos_sale", "POS sale"),
                            ("online_sale", "Online sale"),
                            ("return", "Return"),
                            ("damage", "Damaged"),
                            ("adjustment", "Adjustment"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("quantity_delta", models.IntegerField()),
                ("quantity_before", models.PositiveIntegerField(blank=True, null=True)),
                ("quantity_after", models.PositiveIntegerField(blank=True, null=True)),
                ("reference", models.CharField(blank=True, db_index=True, max_length=80)),
                ("note", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "stockrecord",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mis_movements",
                        to="partner.stockrecord",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["stockrecord", "created_at"], name="mis_stockmovement_stock_created_idx"),
                    models.Index(fields=["movement_type", "created_at"], name="mis_stockmovement_type_created_idx"),
                    models.Index(fields=["reference", "created_at"], name="mis_stockmovement_ref_created_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="mis_stock_movement_nonzero",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity_before__gte=0) | models.Q(quantity_before__isnull=True),
                name="mis_stock_movement_before_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity_after__gte=0) | models.Q(quantity_after__isnull=True),
                name="mis_stock_movement_after_nonnegative",
            ),
        ),
    ]
