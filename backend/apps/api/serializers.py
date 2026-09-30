from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from oscar.core.loading import get_model

from apps.storefront.models import ContactMessage
from apps.mis.models import CashierShift, Expense, PaymentTransaction, POSSale, POSSaleItem, POSSaleReturn, POSSaleReturnItem, Purchase, StockMovement, Supplier\nfrom apps.mis.sale_corrections import POSSaleCorrection, POSSaleCorrectionItem

Category = get_model("catalogue", "Category")
Product = get_model("catalogue", "Product")
User = get_user_model()
Order = get_model("order", "Order")
OrderLine = get_model("order", "Line")


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "product_count")

    def get_product_count(self, category):
        return Product.objects.browsable().filter(categories=category).count()


class ProductSerializer(serializers.ModelSerializer):
    category_names = serializers.SlugRelatedField(
        source="categories", many=True, read_only=True, slug_field="name"
    )
    price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "title", "slug", "upc", "description", "category_names",
            "price", "currency", "image", "in_stock", "available_quantity",
        )

    def _stockrecord(self, product):
        records = list(product.stockrecords.all())
        return records[0] if records else None

    def get_price(self, product):
        record = self._stockrecord(product)
        if not record:
            return None
        price = record.price
        return str(price) if price is not None else None

    def get_currency(self, product):
        record = self._stockrecord(product)
        return record.price_currency if record else None

    def get_image(self, product):
        image = product.images.order_by("display_order", "pk").first()
        if not image or not image.original:
            return None
        try:
            return image.original.url
        except (ValueError, OSError):
            return None

    def get_in_stock(self, product):
        record = self._stockrecord(product)
        return bool(record and (record.num_in_stock is None or record.net_stock_level > 0))

    def get_available_quantity(self, product):
        record = self._stockrecord(product)
        if not record or record.num_in_stock is None:
            return None
        return max(0, record.net_stock_level or 0)


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "email", "phone", "subject", "message", "created_at")
        read_only_fields = ("id", "created_at")


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password", "password_confirm")

    def validate_email(self, value):
        normalized = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        username = f"momand-{uuid4().hex[:16]}"
        user = User.objects.create_user(username=username, password=password, **validated_data)
        customer_group, _ = Group.objects.get_or_create(name="Customer")
        user.groups.add(customer_group)
        return user


class BasketLineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_id = serializers.IntegerField(source="product.id")
    title = serializers.CharField(source="product.get_title")
    slug = serializers.CharField(source="product.slug")
    quantity = serializers.IntegerField()
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_line_total(self, line):
        unit = line.price_incl_tax or line.price_excl_tax or Decimal("0")
        return str(unit * line.quantity)

    def get_unit_price(self, line):
        return str(line.price_incl_tax or line.price_excl_tax or Decimal("0"))

    def get_image(self, line):
        image = line.product.images.order_by("display_order", "pk").first()
        if not image or not image.original:
            return None
        try:
            return image.original.url
        except (ValueError, OSError):
            return None


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ("id", "title", "quantity", "line_price_incl_tax")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(source="lines", many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("number", "date_placed", "status", "currency", "total_incl_tax", "items")


class POSSaleItemSerializer(serializers.ModelSerializer):
    returned_quantity = serializers.SerializerMethodField()
    returnable_quantity = serializers.SerializerMethodField()

    class Meta:
        model = POSSaleItem
        fields = ("id", "title", "sku", "quantity", "returned_quantity", "returnable_quantity", "unit_price", "unit_tax", "line_total")

    def get_returned_quantity(self, item):
        return sum(return_item.quantity for return_item in item.return_items.all())

    def get_returnable_quantity(self, item):
        return item.quantity - self.get_returned_quantity(item)


class POSSalePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ("transaction_ref", "method", "status", "amount", "refunded_amount", "gateway", "paid_at")
        read_only_fields = fields


class POSSaleSerializer(serializers.ModelSerializer):
    items = POSSaleItemSerializer(many=True, read_only=True)
    payments = POSSalePaymentSerializer(source="payment_transactions", many=True, read_only=True)
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)

    class Meta:
        model = POSSale
        fields = ("invoice_number", "created_at", "cashier_name", "currency", "subtotal", "discount", "tax", "total", "payment_method", "amount_tendered", "change_due", "payments", "items")


class POSSaleReturnItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="sale_item.title", read_only=True)

    class Meta:
        model = POSSaleReturnItem
        fields = ("title", "quantity", "refund_amount")


class POSSaleReturnSerializer(serializers.ModelSerializer):
    items = POSSaleReturnItemSerializer(many=True, read_only=True)
    sale_invoice = serializers.CharField(source="sale.invoice_number", read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.get_full_name", read_only=True)

    class Meta:
        model = POSSaleReturn
        fields = ("invoice_number", "sale_invoice", "processed_by_name", "refund_method", "refund_total", "reason", "restocked", "created_at", "items")


class POSSaleReturnInputSerializer(serializers.Serializer):
    sale_item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=100000)


class POSSaleReturnCreateSerializer(serializers.Serializer):
    items = POSSaleReturnInputSerializer(many=True, allow_empty=False)
    refund_method = serializers.ChoiceField(choices=POSSale.PAYMENT_CHOICES)
    reason = serializers.CharField(max_length=240)
    restocked = serializers.BooleanField(default=True)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ("id", "name", "contact_name", "phone", "email", "address", "is_active")


class StockMovementSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="stockrecord.product.get_title", read_only=True)

    class Meta:
        model = StockMovement
        fields = ("id", "product", "movement_type", "quantity_delta", "quantity_before", "quantity_after", "reference", "note", "created_at")


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Purchase
        fields = ("id", "reference", "supplier", "supplier_name", "purchased_at", "currency", "total_cost", "status", "notes", "item_count", "created_at")


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ("id", "category", "description", "amount", "payment_method", "spent_at", "notes", "created_at")
        read_only_fields = ("id", "created_at")


class PaymentTransactionSerializer(serializers.ModelSerializer):
    sale_invoice = serializers.CharField(source="sale.invoice_number", read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "transaction_ref", "sale_invoice", "order_number", "method", "status",
            "amount", "refunded_amount", "gateway", "note", "paid_at", "created_at",
        )
        read_only_fields = fields


class CashierShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)

    class Meta:
        model = CashierShift
        fields = (
            "id", "cashier", "cashier_name", "opened_at", "closed_at",
            "opening_cash", "expected_cash", "closing_cash", "cash_difference",
            "status", "note",
        )
        read_only_fields = ("id", "cashier", "cashier_name", "opened_at", "closed_at", "expected_cash", "cash_difference", "status")
\n\nclass POSSaleCorrectionItemSerializer(serializers.ModelSerializer):\n    title = serializers.CharField(source="sale_item.title", read_only=True)\n\n    class Meta:\n        model = POSSaleCorrectionItem\n        fields = ("title", "original_quantity", "corrected_quantity", "quantity_delta")\n\n\nclass POSSaleCorrectionSerializer(serializers.ModelSerializer):\n    invoice_number = serializers.CharField(source="sale.invoice_number", read_only=True)\n    processed_by_name = serializers.CharField(source="processed_by.get_full_name", read_only=True)\n    items = POSSaleCorrectionItemSerializer(many=True, read_only=True)\n\n    class Meta:\n        model = POSSaleCorrection\n        fields = ("id", "invoice_number", "processed_by_name", "reason", "original_total", "corrected_total", "difference", "created_at", "items")\n\n\nclass POSSaleCorrectionInputItemSerializer(serializers.Serializer):\n    sale_item_id = serializers.IntegerField(min_value=1)\n    corrected_quantity = serializers.IntegerField(min_value=1, max_value=100000)\n\n\nclass POSSaleCorrectionCreateSerializer(serializers.Serializer):\n    items = POSSaleCorrectionInputItemSerializer(many=True, allow_empty=False)\n    reason = serializers.CharField(max_length=240)\n