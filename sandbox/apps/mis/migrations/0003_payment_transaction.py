from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mis", "0002_production_integrity"),
        ("order", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "transaction_ref",
                    models.CharField(
                        editable=False,
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("card", "Card"),
                            ("bank_transfer", "Bank transfer"),
                            ("cod", "Cash on delivery"),
                            ("online", "Online"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                            ("refunded", "Refunded"),
                            ("partially_refunded", "Partially refunded"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=24,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[
                            django.core.validators.MinValueValidator(
                                Decimal("0.01")
                            )
                        ],
                    ),
                ),
                (
                    "refunded_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[
                            django.core.validators.MinValueValidator(
                                Decimal("0.00")
                            )
                        ],
                    ),
                ),
                ("gateway", models.CharField(blank=True, max_length=80)),
                ("note", models.CharField(blank=True, max_length=240)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payment_transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_transactions",
                        to="order.order",
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_transactions",
                        to="mis.possale",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"],
                        name="mis_payment_status_created_idx",
                    ),
                    models.Index(
                        fields=["method", "created_at"],
                        name="mis_payment_method_created_idx",
                    ),
                    models.Index(
                        fields=["sale", "created_at"],
                        name="mis_payment_sale_created_idx",
                    ),
                    models.Index(
                        fields=["order", "created_at"],
                        name="mis_payment_order_created_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="mis_payment_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(
                condition=models.Q(refunded_amount__gte=0),
                name="mis_payment_refunded_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(
                condition=models.Q(refunded_amount__lte=models.F("amount")),
                name="mis_payment_refund_lte_amount",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(sale__isnull=False) & models.Q(order__isnull=True))
                    | (models.Q(sale__isnull=True) & models.Q(order__isnull=False))
                ),
                name="mis_payment_one_order_source",
            ),
        ),
    ]
