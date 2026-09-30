from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def make_pos_invoice_number():
    return f"POS-{timezone.localdate():%Y%m%d}-{uuid4().hex[:10].upper()}"


def make_pos_return_number():
    return f"RET-{timezone.localdate():%Y%m%d}-{uuid4().hex[:10].upper()}"


def default_store_currency():
    return settings.OSCAR_DEFAULT_CURRENCY


class Supplier(models.Model):
    name = models.CharField(max_length=180, unique=True)
    contact_name = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Purchase(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_RECEIVED = "received"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_RECEIVED, "Received")]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchases"
    )
    reference = models.CharField(max_length=80, unique=True)
    currency = models.CharField(max_length=12, default=default_store_currency)
    purchased_at = models.DateField(default=timezone.localdate)
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mis_purchases",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at", "-id"]
        indexes = [
            models.Index(fields=["supplier", "purchased_at"]),
            models.Index(fields=["status", "purchased_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_cost__gte=0),
                name="mis_purchase_total_nonnegative",
            ),
        ]

    def __str__(self):
        return self.reference


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "catalogue.Product",
        on_delete=models.PROTECT,
        related_name="mis_purchase_items",
    )
    stockrecord = models.ForeignKey(
        "partner.StockRecord",
        on_delete=models.PROTECT,
        related_name="mis_purchase_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        indexes = [
            models.Index(fields=["purchase", "product"]),
            models.Index(fields=["stockrecord"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_purchase_item_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="mis_purchase_item_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="mis_purchase_item_total_nonnegative",
            ),
        ]


class POSSale(models.Model):
    PAYMENT_CASH = "cash"
    PAYMENT_CARD = "card"
    PAYMENT_TRANSFER = "bank_transfer"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_CARD, "Card"),
        (PAYMENT_TRANSFER, "Bank transfer"),
    ]

    invoice_number = models.CharField(
        max_length=32,
        unique=True,
        default=make_pos_invoice_number,
        editable=False,
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pos_sales",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pos_purchases",
    )
    currency = models.CharField(max_length=12)
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    amount_tendered = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    change_due = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at", "cashier"]),
            models.Index(fields=["created_at", "payment_method"]),
            models.Index(fields=["customer", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
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
        ]

    def __str__(self):
        return self.invoice_number


class POSSaleItem(models.Model):
    sale = models.ForeignKey(
        POSSale, on_delete=models.PROTECT, related_name="items"
    )
    product = models.ForeignKey(
        "catalogue.Product",
        on_delete=models.PROTECT,
        related_name="pos_sale_items",
    )
    stockrecord = models.ForeignKey(
        "partner.StockRecord",
        on_delete=models.PROTECT,
        related_name="pos_sale_items",
    )
    title = models.CharField(max_length=255)
    sku = models.CharField(max_length=128, blank=True)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    unit_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        indexes = [
            models.Index(fields=["sale", "product"]),
            models.Index(fields=["stockrecord"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_pos_sale_item_qty_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(unit_price__gte=0)
                    & models.Q(unit_tax__gte=0)
                    & models.Q(line_total__gte=0)
                ),
                name="mis_pos_sale_item_amounts_nonnegative",
            ),
        ]


class POSSaleReturn(models.Model):
    invoice_number = models.CharField(
        max_length=32,
        unique=True,
        default=make_pos_return_number,
        editable=False,
    )
    sale = models.ForeignKey(
        POSSale, on_delete=models.PROTECT, related_name="returns"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pos_returns",
    )
    refund_method = models.CharField(
        max_length=20,
        choices=POSSale.PAYMENT_CHOICES,
    )
    refund_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reason = models.CharField(max_length=240)
    restocked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sale", "created_at"]),
            models.Index(fields=["refund_method", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(refund_total__gte=0),
                name="mis_pos_return_total_nonnegative",
            ),
        ]


class POSSaleReturnItem(models.Model):
    sale_return = models.ForeignKey(
        POSSaleReturn,
        on_delete=models.PROTECT,
        related_name="items",
    )
    sale_item = models.ForeignKey(
        POSSaleItem,
        on_delete=models.PROTECT,
        related_name="return_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    refund_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        indexes = [
            models.Index(fields=["sale_return", "sale_item"]),
            models.Index(fields=["sale_item"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="mis_pos_return_item_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(refund_amount__gte=0),
                name="mis_pos_return_item_amount_nonnegative",
            ),
        ]


class StockMovement(models.Model):
    TYPE_OPENING = "opening"
    TYPE_PURCHASE = "purchase"
    TYPE_POS_SALE = "pos_sale"
    TYPE_ONLINE_SALE = "online_sale"
    TYPE_RETURN = "return"
    TYPE_DAMAGE = "damage"
    TYPE_ADJUSTMENT = "adjustment"
    TYPE_CHOICES = [
        (TYPE_OPENING, "Opening stock"),
        (TYPE_PURCHASE, "Purchase"),
        (TYPE_POS_SALE, "POS sale"),
        (TYPE_ONLINE_SALE, "Online sale"),
        (TYPE_RETURN, "Return"),
        (TYPE_DAMAGE, "Damaged"),
        (TYPE_ADJUSTMENT, "Adjustment"),
    ]

    stockrecord = models.ForeignKey(
        "partner.StockRecord",
        on_delete=models.PROTECT,
        related_name="mis_movements",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
    )
    quantity_delta = models.IntegerField()
    quantity_before = models.PositiveIntegerField(null=True, blank=True)
    quantity_after = models.PositiveIntegerField(null=True, blank=True)
    reference = models.CharField(max_length=80, blank=True, db_index=True)
    note = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["stockrecord", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["reference", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="mis_stock_movement_nonzero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantity_before__gte=0)
                    | models.Q(quantity_before__isnull=True)
                ),
                name="mis_stock_movement_before_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantity_after__gte=0)
                    | models.Q(quantity_after__isnull=True)
                ),
                name="mis_stock_movement_after_nonnegative",
            ),
        ]


class Expense(models.Model):
    CATEGORY_ELECTRICITY = "electricity"
    CATEGORY_RENT = "rent"
    CATEGORY_SALARY = "salary"
    CATEGORY_TRANSPORT = "transportation"
    CATEGORY_INTERNET = "internet"
    CATEGORY_MAINTENANCE = "maintenance"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_ELECTRICITY, "Electricity"),
        (CATEGORY_RENT, "Rent"),
        (CATEGORY_SALARY, "Salary"),
        (CATEGORY_TRANSPORT, "Transportation"),
        (CATEGORY_INTERNET, "Internet"),
        (CATEGORY_MAINTENANCE, "Maintenance"),
        (CATEGORY_OTHER, "Other"),
    ]
    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("bank_transfer", "Bank transfer"),
        ("other", "Other"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=240)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="cash",
    )
    spent_at = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mis_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-spent_at", "-id"]
        indexes = [
            models.Index(fields=["category", "spent_at"]),
            models.Index(fields=["payment_method", "spent_at"]),
        ]

    def __str__(self):
        return self.description
