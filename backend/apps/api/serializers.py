from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers

from oscar.core.loading import get_model

from apps.storefront.models import ContactMessage
from apps.storefront.models import StoreSettings
from apps.mis.models import CashierShift, Expense, PaymentTransaction, POSSale, POSSaleItem, POSSaleReturn, POSSaleReturnItem, Purchase, StockMovement, Supplier
from apps.mis.sale_corrections import POSSaleCorrection, POSSaleCorrectionItem, POSSaleCorrectionRequest

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
        image = min(product.images.all(), key=lambda item: (item.display_order, item.pk), default=None)
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


class StaffUserSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_active", "groups", "permissions")

    def get_permissions(self, user):
        return sorted(f"{app_label}.{codename}" for app_label, codename in user.user_permissions.values_list("content_type__app_label", "codename"))


class StaffUserWriteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    password = serializers.CharField(required=False, write_only=True, min_length=9)
    is_active = serializers.BooleanField(required=False, default=True)
    group_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    permissions = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value.lower()

    def validate(self, attrs):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.auth.password_validation import validate_password
        group_ids = attrs.get("group_ids", [])
        if len(set(group_ids)) != len(group_ids) or Group.objects.filter(pk__in=group_ids).count() != len(group_ids):
            raise serializers.ValidationError({"group_ids": "Choose valid roles."})
        if not self.context.get("request").user.is_superuser and Group.objects.filter(pk__in=group_ids, name="Super Admin").exists():
            raise serializers.ValidationError({"group_ids": "Only a superuser can assign the Super Admin role."})
        codes = attrs.get("permissions", [])
        if len(set(codes)) != len(codes):
            raise serializers.ValidationError({"permissions": "Remove duplicate permissions."})
        valid = set(Permission.objects.exclude(content_type__app_label__in=("auth", "contenttypes", "sessions")).values_list("content_type__app_label", "codename"))
        if any("." not in code or tuple(code.split(".", 1)) not in valid for code in codes):
            raise serializers.ValidationError({"permissions": "One or more permissions are invalid."})
        password = attrs.get("password")
        if not self.instance and not password:
            raise serializers.ValidationError({"password": "A password is required for a new user."})
        if password:
            validate_password(password)
        return attrs

    def save(self, **kwargs):
        from django.contrib.auth.models import Group, Permission
        data = self.validated_data.copy()
        password = data.pop("password", None)
        group_ids = data.pop("group_ids", [])
        codes = data.pop("permissions", [])
        data["is_staff"] = True
        user = self.instance
        if user is None:
            user = User(username=f"momand-{uuid4().hex[:16]}", **data)
            user.set_password(password)
        else:
            for field, value in data.items():
                setattr(user, field, value)
            if password:
                user.set_password(password)
        user.save()
        user.groups.set(Group.objects.filter(pk__in=group_ids))
        filters = Q(pk__in=[])
        for code in codes:
            app_label, codename = code.split(".", 1)
            filters |= Q(content_type__app_label=app_label, codename=codename)
        user.user_permissions.set(Permission.objects.filter(filters))
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
        image = min(line.product.images.all(), key=lambda item: (item.display_order, item.pk), default=None)
        if not image or not image.original:
            return None
        try:
            return image.original.url
        except (ValueError, OSError):
            return None


class OrderLineSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = ("id", "title", "quantity", "line_price_incl_tax", "image")

    def get_image(self, line):
        product = getattr(line, "product", None)
        image = min(product.images.all(), key=lambda item: (item.display_order, item.pk), default=None) if product else None
        if not image or not image.original:
            return None
        try:
            return image.original.url
        except (ValueError, OSError):
            return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(source="lines", many=True, read_only=True)
    payment_method = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("number", "date_placed", "status", "currency", "total_incl_tax", "payment_method", "payment_status", "items")

    def get_payment(self, order):
        return next(iter(order.payment_transactions.all()), None)

    def get_payment_method(self, order):
        payment = self.get_payment(order)
        return payment.method if payment else ""

    def get_payment_status(self, order):
        payment = self.get_payment(order)
        return payment.status if payment else ""


class AdminOrderSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="user.email", read_only=True, allow_null=True)
    customer_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    items = OrderLineSerializer(source="lines", many=True, read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "number", "date_placed", "status", "currency", "total_incl_tax",
            "customer_name", "customer_email", "phone", "delivery_address", "items", "payment",
        )

    def get_customer_name(self, order):
        address = getattr(order, "shipping_address", None)
        if address:
            return " ".join(part for part in (address.first_name, address.last_name) if part)
        return order.user.get_full_name() if order.user_id else "Guest"

    def get_phone(self, order):
        address = getattr(order, "shipping_address", None)
        return address.phone_number if address else ""

    def get_delivery_address(self, order):
        address = getattr(order, "shipping_address", None)
        if not address:
            return ""
        return ", ".join(part for part in (address.line1, address.line2, address.line3, address.line4, address.country.printable_name if address.country_id else "") if part)

    def get_payment(self, order):
        payment = next(iter(order.payment_transactions.all()), None)
        if not payment:
            return None
        return {"method": payment.method, "status": payment.status, "transaction_ref": payment.transaction_ref}


class StaffCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "date_joined", "is_active")


class POSSaleCustomerSerializer(serializers.Serializer):
    customer_name = serializers.CharField(allow_blank=True)
    customer_phone = serializers.CharField(allow_blank=True)
    sales_count = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=14, decimal_places=2)
    last_sale = serializers.DateTimeField()


class ProductImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, image):
        if image.size > 8 * 1024 * 1024:
            raise serializers.ValidationError("Image files must be 8 MB or smaller.")
        return image


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = (
            "store_name", "tagline", "currency", "tax_rate", "phone", "email", "address",
            "payment_methods", "bank_transfer_instructions",
        )

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Enter a three-letter currency code.")
        return value

    def validate_payment_methods(self, value):
        methods = StoreSettings.PAYMENT_METHODS
        if not isinstance(value, list) or not value or any(method not in methods for method in value):
            raise serializers.ValidationError("Select at least one supported payment method.")
        return list(dict.fromkeys(value))

    def validate(self, attrs):
        methods = attrs.get("payment_methods", getattr(self.instance, "payment_methods", ["cod"]))
        instructions = attrs.get("bank_transfer_instructions", getattr(self.instance, "bank_transfer_instructions", ""))
        if "bank_transfer" in methods and not str(instructions).strip():
            raise serializers.ValidationError({"bank_transfer_instructions": "Add transfer instructions before enabling bank transfer."})
        tax_rate = attrs.get("tax_rate", getattr(self.instance, "tax_rate", Decimal("0")))
        if tax_rate < 0 or tax_rate > 1:
            raise serializers.ValidationError({"tax_rate": "Tax rate must be between 0 and 1 (0% to 100%)."})
        return attrs


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
    amount_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()

    def get_amount_paid(self, sale):
        return sum(
            (payment.amount for payment in sale.payment_transactions.all()
             if payment.status == PaymentTransaction.STATUS_PAID),
            Decimal("0.00"),
        )

    def get_balance_due(self, sale):
        return max(Decimal("0.00"), sale.total - self.get_amount_paid(sale))

    class Meta:
        model = POSSale
        fields = ("invoice_number", "created_at", "cashier_name", "customer_name", "customer_phone", "currency", "subtotal", "discount", "tax", "total", "amount_paid", "balance_due", "payment_method", "amount_tendered", "change_due", "payments", "items")


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


class POSSaleCorrectionItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="sale_item.title", read_only=True)

    class Meta:
        model = POSSaleCorrectionItem
        fields = ("title", "original_quantity", "corrected_quantity", "quantity_delta")


class POSSaleCorrectionSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="sale.invoice_number", read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.get_full_name", read_only=True)
    items = POSSaleCorrectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = POSSaleCorrection
        fields = ("id", "invoice_number", "processed_by_name", "reason", "original_total", "corrected_total", "difference", "created_at", "items")


class POSSaleCorrectionInputItemSerializer(serializers.Serializer):
    sale_item_id = serializers.IntegerField(min_value=1)
    corrected_quantity = serializers.IntegerField(min_value=1, max_value=100000)


class POSSaleCorrectionCreateSerializer(serializers.Serializer):
    items = POSSaleCorrectionInputItemSerializer(many=True, allow_empty=False)
    reason = serializers.CharField(max_length=240)


class POSSaleCorrectionRequestSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="sale.invoice_number", read_only=True)
    cashier_name = serializers.SerializerMethodField()

    class Meta:
        model = POSSaleCorrectionRequest
        fields = ("id", "invoice_number", "cashier_name", "reason", "created_at", "is_resolved")

    def get_cashier_name(self, request):
        cashier = request.sale.cashier
        return cashier.get_full_name() or cashier.email or cashier.get_username()


class POSSaleCorrectionRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=240, trim_whitespace=True)
