import io
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Max, Q
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import serializers as drf_serializers

from oscar.core.loading import get_model
from oscar.apps.shipping.methods import Free
from oscar.apps.checkout.calculators import OrderTotalCalculator
from oscar.apps.order.utils import OrderCreator

from .permissions import HasAnyMISPermission, StaffWriteCustomerReadOnly
from .permissions import effective_staff_permissions
from .serializers import (
    AdminOrderSerializer,
    BasketLineSerializer,
    CategorySerializer,
    ContactMessageSerializer,
    RegistrationSerializer,
    OrderSerializer,
    POSSaleSerializer,
    ProductSerializer,
    ProductImageUploadSerializer,
    PurchaseSerializer,
    StockMovementSerializer,
    SupplierSerializer,
    ExpenseSerializer,
    POSSaleReturnSerializer,
    POSSaleReturnCreateSerializer,
    POSSaleCorrectionSerializer,
    POSSaleCorrectionCreateSerializer,
    POSSaleCorrectionRequestSerializer,
    POSSaleCorrectionRequestCreateSerializer,
    PaymentTransactionSerializer,
    CashierShiftSerializer,
    StaffUserSerializer,
    StaffUserWriteSerializer,
    StaffCustomerSerializer,
    POSSaleCustomerSerializer,
    StoreSettingsSerializer,
)
from .services import add_to_basket, get_session_basket
from .permissions import HasMISPermission
from apps.mis.models import CashierShift, Expense, OnlineOrderCost, PaymentTransaction, POSSale, POSSaleItem, POSSaleReturn, Purchase, StockMovement, Supplier
from apps.mis.services import adjust_stock, close_cashier_shift, collect_pos_balance, create_pos_sale, open_cashier_shift, process_pos_return, receive_purchase
from apps.mis.sale_corrections import POSSaleCorrectionRequest
from apps.mis.sale_correction_services import correct_pos_sale
from apps.mis.accounting import financial_summary
from apps.storefront.models import StoreSettings, current_store_settings

Category = get_model("catalogue", "Category")
Product = get_model("catalogue", "Product")
StockRecord = get_model("partner", "StockRecord")
Order = get_model("order", "Order")
ShippingAddress = get_model("order", "ShippingAddress")
Country = get_model("address", "Country")


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (StaffWriteCustomerReadOnly,)
    lookup_field = "slug"
    search_fields = ("title", "upc", "description", "categories__name")
    ordering_fields = ("title", "date_created", "stockrecords__price")
    ordering = ("title",)

    def get_queryset(self):
        queryset = Product.objects.browsable().prefetch_related(
            "categories", "images", "stockrecords"
        ).distinct()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(categories__slug=category)
        minimum = self.request.query_params.get("min_price")
        maximum = self.request.query_params.get("max_price")
        if minimum:
            queryset = queryset.filter(stockrecords__price__gte=minimum)
        if maximum:
            queryset = queryset.filter(stockrecords__price__lte=maximum)
        if self.request.query_params.get("available") == "true":
            queryset = queryset.filter(
                stockrecords__num_in_stock__gt=Coalesce(
                    F("stockrecords__num_allocated"), 0
                )
            )
        return queryset


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.all().order_by("name")


class StoreConfigView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        config = current_store_settings()
        methods = config["payment_methods"] if isinstance(config, dict) else config.payment_methods
        instructions = config["bank_transfer_instructions"] if isinstance(config, dict) else config.bank_transfer_instructions
        return Response({
            "name": config["store_name"] if isinstance(config, dict) else config.store_name,
            "tagline": config["tagline"] if isinstance(config, dict) else config.tagline,
            "currency": config["currency"] if isinstance(config, dict) else config.currency,
            "tax_rate": str(config["tax_rate"] if isinstance(config, dict) else config.tax_rate),
            "phone": config["phone"] if isinstance(config, dict) else config.phone,
            "email": config["email"] if isinstance(config, dict) else config.email,
            "address": config["address"] if isinstance(config, dict) else config.address,
            "payment_methods": [
                {"code": code, "name": StoreSettings.PAYMENT_METHODS[code]}
                for code in methods if code in StoreSettings.PAYMENT_METHODS
            ],
            "bank_transfer_instructions": instructions if "bank_transfer" in methods else "",
        })


class StoreSettingsView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "storefront.change_storesettings"

    def get_object(self):
        defaults = current_store_settings()
        if isinstance(defaults, StoreSettings):
            defaults = {field: getattr(defaults, field) for field in (
                "store_name", "tagline", "currency", "tax_rate", "phone", "email", "address",
                "payment_methods", "bank_transfer_instructions",
            )}
        obj, _ = StoreSettings.objects.get_or_create(pk=1, defaults=defaults)
        return obj

    def get(self, request):
        serializer = StoreSettingsSerializer(self.get_object())
        return Response(serializer.data)

    def patch(self, request):
        serializer = StoreSettingsSerializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OnlineOrderListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "order.view_order"
    serializer_class = AdminOrderSerializer

    def get_queryset(self):
        queryset = Order.objects.select_related("user", "shipping_address", "shipping_address__country").prefetch_related(
            "lines__product__images", "payment_transactions",
        ).order_by("-date_placed")
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search", "").strip()[:120]
        if status_filter:
            queryset = queryset.filter(status__iexact=status_filter)
        if search:
            queryset = queryset.filter(
                Q(number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(shipping_address__first_name__icontains=search)
                | Q(shipping_address__last_name__icontains=search)
                | Q(shipping_address__phone_number__icontains=search)
            ).distinct()
        return queryset


class StaffCustomerListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "customer.view_user"
    serializer_class = StaffCustomerSerializer

    def get_queryset(self):
        queryset = get_user_model().objects.filter(is_staff=False).order_by("-date_joined")
        search = self.request.query_params.get("search", "").strip()[:120]
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return queryset


class POSSaleCustomerListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale_all"
    serializer_class = POSSaleCustomerSerializer

    def get_queryset(self):
        queryset = POSSale.objects.exclude(Q(customer_name="") & Q(customer_phone="")).values(
            "customer_name", "customer_phone",
        ).annotate(
            sales_count=Count("pk"),
            total_spent=Sum("total"),
            last_sale=Max("created_at"),
        ).order_by("-last_sale")
        search = self.request.query_params.get("search", "").strip()[:120]
        if search:
            queryset = queryset.filter(Q(customer_name__icontains=search) | Q(customer_phone__icontains=search))
        return queryset


class ProductImageUploadView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, product_id):
        if not request.user.is_staff or not (
            request.user.has_perm("catalogue.change_product")
            or request.user.groups.filter(name__in=("Admin", "Super Admin")).exists()
        ):
            return Response({"detail": "You do not have permission to update product images."}, status=403)
        ProductImage = get_model("catalogue", "ProductImage")
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        ProductImage.objects.filter(product=product).update(display_order=F("display_order") + 1)
        saved = ProductImage.objects.create(product=product, original=image, display_order=0)
        return Response({"product_id": product.pk, "image": saved.original.url}, status=201)


class StoreBackupDownloadView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not request.user.is_superuser:
            return Response({"detail": "Only a superuser can download a full store backup."}, status=403)
        output = tempfile.TemporaryFile(mode="w+b")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            with archive.open("database.json", "w") as binary_stream:
                text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")
                call_command(
                    "dumpdata", "--natural-foreign", "--natural-primary",
                    "--exclude=contenttypes", "--exclude=auth.permission", "--exclude=sessions",
                    "--exclude=token_blacklist", "--indent=2",
                    stdout=text_stream,
                )
                text_stream.flush()
                text_stream.detach()
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                for path in media_root.rglob("*"):
                    if path.is_file():
                        archive.write(path, f"media/{path.relative_to(media_root).as_posix()}")
            archive.writestr("README.txt", "Momand Super Store backup\n\nContains database.json and uploaded media files. Keep this archive private. Restore the database with Django loaddata after migrating, then copy the media folder into MEDIA_ROOT.\n")
        output.seek(0)
        filename = f"momand-store-backup-{timezone.localtime():%Y%m%d-%H%M%S}.zip"
        return FileResponse(output, as_attachment=True, filename=filename, content_type="application/zip")


class StaffUsersView(APIView):
    permission_classes = (IsAuthenticated,)

    def _allowed(self, user, verb):
        return user.is_superuser or (user.is_staff and (
            user.has_perm(f"auth.{verb}_user")
            or user.groups.filter(name__in=("Admin", "Super Admin")).exists()
        ))

    def get(self, request):
        if not self._allowed(request.user, "view"):
            return Response({"detail": "You do not have permission to manage staff users."}, status=403)
        User = get_user_model()
        users = User.objects.filter(is_staff=True).prefetch_related("groups", "user_permissions").order_by("email")
        groups = Group.objects.exclude(name="Customer")
        if not request.user.is_superuser:
            groups = groups.exclude(name="Super Admin")
        groups = groups.order_by("name")
        permissions = Permission.objects.exclude(content_type__app_label__in=("auth", "contenttypes", "sessions")).select_related("content_type").order_by("content_type__app_label", "codename")
        return Response({
            "users": StaffUserSerializer(users, many=True).data,
            "roles": [{"id": group.pk, "name": group.name} for group in groups],
            "permissions": [{"code": f"{perm.content_type.app_label}.{perm.codename}", "name": str(perm), "module": perm.content_type.app_label} for perm in permissions],
        })

    def post(self, request):
        if not self._allowed(request.user, "add"):
            return Response({"detail": "You do not have permission to add staff users."}, status=403)
        serializer = StaffUserWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(StaffUserSerializer(user).data, status=201)

    def patch(self, request, user_id):
        if not self._allowed(request.user, "change"):
            return Response({"detail": "You do not have permission to change staff users."}, status=403)
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id, is_staff=True, is_superuser=False)
        serializer = StaffUserWriteSerializer(user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(StaffUserSerializer(serializer.save()).data)


class CountryListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        countries = Country.objects.filter(is_shipping_country=True).order_by("printable_name")
        return Response({"results": [{"code": country.iso_3166_1_a2, "name": country.printable_name} for country in countries]})


class ContactMessageCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (AnonRateThrottle,)
    queryset = None


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (AnonRateThrottle,)
    queryset = None


class CurrentUserView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        return Response({
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "groups": list(user.groups.values_list("name", flat=True)),
            "permissions": effective_staff_permissions(user),
            "can_manage_users": bool(user.is_superuser or user.has_perm("auth.view_user") or user.groups.filter(name__in=("Admin", "Super Admin")).exists()),
            "can_correct_sales": bool(user.is_staff and user.has_perm("mis.change_possale")),
        })


class CustomerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "number"
    lookup_url_kwarg = "number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "lines__product__images", "payment_transactions",
        ).order_by("-date_placed")


class BasketView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        basket = get_session_basket(request)
        if basket is None:
            return Response({"items": [], "count": 0, "total": "0.00", "currency": "AFN"})
        lines = list(basket.all_lines())
        data = BasketLineSerializer(lines, many=True).data
        return Response({
            "items": data,
            "count": sum(line.quantity for line in lines),
            "total": str(basket.total_incl_tax if basket.is_tax_known else basket.total_excl_tax),
            "currency": basket.currency,
        })

    def post(self, request):
        basket = get_session_basket(request)
        if basket is None:
            return Response({"detail": "Could not initialize a shopping basket."}, status=500)
        product = get_object_or_404(Product.objects.browsable(), pk=request.data.get("product_id"))
        try:
            quantity = int(request.data.get("quantity", 1))
            if quantity < 1 or quantity > 999:
                raise ValueError("Quantity must be between 1 and 999.")
            add_to_basket(basket, product, quantity)
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        basket = get_session_basket(request)
        lines = list(basket.all_lines())
        return Response({
            "items": BasketLineSerializer(lines, many=True).data,
            "count": sum(line.quantity for line in lines),
            "total": str(basket.total_incl_tax if basket.is_tax_known else basket.total_excl_tax),
            "currency": basket.currency,
        }, status=status.HTTP_200_OK)

    @staticmethod
    def response_for(basket):
        lines = list(basket.all_lines())
        return Response({
            "items": BasketLineSerializer(lines, many=True).data,
            "count": sum(line.quantity for line in lines),
            "total": str(basket.total_incl_tax if basket.is_tax_known else basket.total_excl_tax),
            "currency": basket.currency,
        })


class BasketItemView(APIView):
    permission_classes = (AllowAny,)

    def patch(self, request, line_id):
        basket = get_session_basket(request)
        if basket is None:
            return Response({"detail": "Basket not found."}, status=status.HTTP_404_NOT_FOUND)
        line = get_object_or_404(basket.lines, pk=line_id)
        try:
            quantity = int(request.data.get("quantity", 0))
            if quantity < 1 or quantity > 999:
                raise ValueError("Quantity must be between 1 and 999.")
            available = line.stockrecord.net_stock_level if line.stockrecord.num_in_stock is not None else None
            if available is not None and quantity > available:
                raise ValueError("There is not enough stock for the requested quantity.")
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        line.quantity = quantity
        line.save(update_fields=["quantity"])
        basket.reset_offer_applications()
        return BasketView.response_for(basket)

    def delete(self, request, line_id):
        basket = get_session_basket(request)
        if basket is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        line = get_object_or_404(basket.lines, pk=line_id)
        line.delete()
        basket.reset_offer_applications()
        return BasketView.response_for(basket)


class CheckoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        basket = get_session_basket(request)
        if basket is None or basket.is_empty:
            return Response({"detail": "Your basket is empty."}, status=400)
        data = request.data
        required = ("first_name", "last_name", "phone", "address", "city", "country")
        errors = {field: "This field is required." for field in required if not str(data.get(field, "")).strip()}
        if errors:
            return Response(errors, status=400)
        method = str(data.get("payment_method", "cod"))
        config = current_store_settings()
        enabled_methods = config["payment_methods"] if isinstance(config, dict) else config.payment_methods
        if method not in enabled_methods:
            return Response({"payment_method": "Choose one of the payment methods currently offered by the store."}, status=400)
        try:
            country = Country.objects.get(iso_3166_1_a2=str(data["country"]).upper())
        except Country.DoesNotExist:
            return Response({"country": "Choose a supported delivery country."}, status=400)

        try:
            with transaction.atomic():
                basket_lines = list(basket.all_lines())
                stockrecord_ids = sorted({line.stockrecord_id for line in basket_lines})
                locked_records = {
                    record.pk: record
                    for record in StockRecord.objects.select_for_update().filter(
                        pk__in=stockrecord_ids
                    ).order_by("pk")
                }
                if len(locked_records) != len(stockrecord_ids):
                    return Response({"detail": "One or more products are no longer available."}, status=409)

                for line in basket_lines:
                    record = locked_records[line.stockrecord_id]
                    if (
                        record.num_in_stock is not None
                        and record.net_stock_level < line.quantity
                    ):
                        return Response(
                            {"detail": f"Insufficient stock for {line.product.get_title()}."},
                            status=409,
                        )

                address = ShippingAddress(
                    first_name=str(data["first_name"]).strip()[:255],
                    last_name=str(data["last_name"]).strip()[:255],
                    line1=str(data["address"]).strip()[:255],
                    line2=str(data.get("district", "")).strip()[:255],
                    line3=str(data.get("province", "")).strip()[:255],
                    line4=str(data["city"]).strip()[:255],
                    phone_number=str(data["phone"]).strip()[:32],
                    notes=str(data.get("delivery_notes", "")).strip(),
                    country=country,
                )
                shipping = Free()
                charge = shipping.calculate(basket)
                total = OrderTotalCalculator(request).calculate(basket, charge)
                order = OrderCreator().place_order(
                    basket=basket,
                    total=total,
                    shipping_method=shipping,
                    shipping_charge=charge,
                    user=request.user,
                    shipping_address=address,
                    request=request,
                )

                PaymentTransaction.objects.create(
                    transaction_ref=f"WEB-{order.number}-{uuid4().hex[:8].upper()}",
                    order=order,
                    method=method,
                    status=PaymentTransaction.STATUS_PENDING,
                    amount=order.total_incl_tax,
                    note="Awaiting payment confirmation.",
                    created_by=request.user,
                )

                # Oscar creates the order, while this custom ledger snapshots
                # the inventory cost used for COGS before stock is deducted.
                for line in basket_lines:
                    record = locked_records[line.stockrecord_id]
                    if record.cost_price is None:
                        raise ValidationError(
                            f"Set an inventory cost for {line.product.get_title()} before online sale."
                        )
                    OnlineOrderCost.objects.create(
                        order=order,
                        product=line.product,
                        stockrecord=record,
                        quantity=line.quantity,
                        unit_cost=record.cost_price,
                        cost_total=record.cost_price * line.quantity,
                    )

                # Deduct physical stock while the same row locks are held.
                for line in basket_lines:
                    record = locked_records[line.stockrecord_id]
                    if record.num_in_stock is not None:
                        before = max(0, record.net_stock_level or 0)
                        if line.quantity > before:
                            raise ValidationError(
                                f"Insufficient stock for {line.product.get_title()}."
                            )
                        record.num_in_stock -= line.quantity
                        record.save(update_fields=["num_in_stock"])
                        StockMovement.objects.create(
                            stockrecord=record,
                            movement_type=StockMovement.TYPE_ONLINE_SALE,
                            quantity_delta=-line.quantity,
                            quantity_before=before,
                            quantity_after=max(0, record.net_stock_level or 0),
                            reference=order.number,
                            note="Online checkout",
                            created_by=request.user,
                        )

                basket.submit()
        except (ObjectDoesNotExist, ValueError, ValidationError) as exc:
            return Response({"detail": str(exc) or "The order could not be placed."}, status=400)
        return Response(OrderSerializer(order).data, status=201)


class POSProductSearchView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "catalogue.view_product"

    def get(self, request):
        term = str(request.query_params.get("search", "")).strip()[:128]
        if not term:
            return Response({"results": []})
        matches = Product.objects.browsable().filter(Q(title__icontains=term) | Q(upc__iexact=term)).prefetch_related("categories", "images", "stockrecords").distinct()[:30]
        return Response({"results": ProductSerializer(matches, many=True).data})


class POSSaleListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"
    serializer_class = POSSaleSerializer
    queryset = POSSale.objects.prefetch_related("items__return_items", "payment_transactions").select_related("cashier", "customer")
    filterset_fields = ("payment_method", "cashier")
    ordering_fields = ("created_at", "total")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("mis.view_possale_all"):
            queryset = queryset.filter(cashier=self.request.user)
        return queryset


class POSSaleOutstandingBalancesView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"

    def get(self, request):
        from decimal import Decimal

        sales = POSSale.objects.annotate(
            amount_paid=Coalesce(
                Sum("payment_transactions__amount", filter=Q(payment_transactions__status=PaymentTransaction.STATUS_PAID)),
                Decimal("0.00"),
            ),
        ).annotate(balance_due=F("total") - F("amount_paid")).filter(balance_due__gt=0)
        sales = sales.select_related("cashier", "customer").prefetch_related(
            "items__return_items", "payment_transactions",
        ).order_by("-created_at")
        return Response(POSSaleSerializer(sales, many=True).data)


class POSSaleCreateView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.add_possale"

    def post(self, request):
        try:
            sale = create_pos_sale(
                cashier=request.user,
                items=request.data.get("items"),
                payment_method=request.data.get("payment_method", "cash"),
                amount_tendered=request.data.get("amount_tendered"),
                payment_lines=request.data.get("payment_lines"),
                customer_id=request.data.get("customer_id"),
                customer_name=request.data.get("customer_name", ""),
                customer_phone=request.data.get("customer_phone", ""),
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=400)
        return Response(POSSaleSerializer(sale).data, status=201)


class POSSaleDetailView(generics.RetrieveAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"
    serializer_class = POSSaleSerializer
    queryset = POSSale.objects.prefetch_related("items__return_items", "payment_transactions").select_related("cashier", "customer")
    lookup_field = "invoice_number"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("mis.view_possale_all"):
            queryset = queryset.filter(cashier=self.request.user)
        return queryset


class POSSaleBalancePaymentView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"

    def post(self, request, invoice_number):
        try:
            sale = collect_pos_balance(
                invoice_number=invoice_number,
                received_by=request.user,
                payment_method=request.data.get("payment_method"),
                amount_tendered=request.data.get("amount_tendered"),
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(POSSaleSerializer(sale).data)


class POSSaleReturnCreateView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.add_possalereturn"

    def post(self, request, invoice_number):
        serializer = POSSaleReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            returned = process_pos_return(
                invoice_number=invoice_number,
                processed_by=request.user,
                **serializer.validated_data,
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=400)
        return Response(POSSaleReturnSerializer(returned).data, status=201)


class POSSaleReturnListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possalereturn"
    serializer_class = POSSaleReturnSerializer
    queryset = POSSaleReturn.objects.select_related("sale", "processed_by").prefetch_related("items")


class PaymentTransactionListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_paymenttransaction"
    serializer_class = PaymentTransactionSerializer
    queryset = PaymentTransaction.objects.select_related("sale", "order", "created_by").all()
    filterset_fields = ("method", "status", "gateway")
    ordering_fields = ("created_at", "amount")
    ordering = ("-created_at",)


class PaymentTransactionUpdateView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.change_paymenttransaction"

    def patch(self, request, transaction_ref):
        payment = get_object_or_404(PaymentTransaction, transaction_ref=transaction_ref)
        if payment.status != PaymentTransaction.STATUS_PENDING:
            return Response({"detail": "Only pending payments can be marked received."}, status=400)
        if request.data.get("status") != PaymentTransaction.STATUS_PAID:
            return Response({"status": "Set the status to paid to confirm receipt."}, status=400)
        payment.status = PaymentTransaction.STATUS_PAID
        payment.paid_at = timezone.now()
        note = str(request.data.get("note", "")).strip()
        if note:
            payment.note = note[:240]
        payment.save(update_fields=["status", "paid_at", "note"])
        return Response(PaymentTransactionSerializer(payment).data)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all()
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_supplier"

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            self.required_permission = "mis.view_supplier"
        elif self.request.method == "POST":
            self.required_permission = "mis.add_supplier"
        elif self.request.method == "DELETE":
            self.required_permission = "mis.delete_supplier"
        else:
            self.required_permission = "mis.change_supplier"
        return super().get_permissions()


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.select_related("created_by").all()
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_expense"
    filterset_fields = ("category", "payment_method", "spent_at")
    ordering_fields = ("spent_at", "amount", "created_at")
    ordering = ("-spent_at", "-id")
    http_method_names = ("get", "post", "head", "options")

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            self.required_permission = "mis.view_expense"
        elif self.request.method == "POST":
            self.required_permission = "mis.add_expense"
        elif self.request.method == "DELETE":
            self.required_permission = "mis.delete_expense"
        else:
            self.required_permission = "mis.change_expense"
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PurchaseListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_purchase"
    serializer_class = PurchaseSerializer
    queryset = Purchase.objects.select_related("supplier").prefetch_related("items")


class PurchaseReceiveView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.add_purchase"

    def post(self, request):
        data = request.data
        try:
            supplier = Supplier.objects.get(pk=data.get("supplier_id"), is_active=True)
        except (Supplier.DoesNotExist, TypeError, ValueError):
            return Response({"supplier_id": "Choose an active supplier."}, status=400)
        reference = str(data.get("reference", "")).strip()
        if not reference or len(reference) > 80:
            return Response({"reference": "Enter a supplier invoice reference (up to 80 characters)."}, status=400)
        try:
            purchased_at = parse_date(str(data.get("purchased_at"))) if data.get("purchased_at") else timezone.localdate()
            if purchased_at is None:
                raise ValueError("Invalid purchase date")
            purchase = receive_purchase(
                supplier=supplier, reference=reference, purchased_at=purchased_at,
                items=data.get("items"), created_by=request.user,
                notes=str(data.get("notes", ""))[:2000],
            )
        except IntegrityError:
            return Response({"reference": "This invoice reference has already been recorded."}, status=409)
        except (drf_serializers.ValidationError, ValueError, TypeError) as exc:
            details = exc.detail if isinstance(exc, drf_serializers.ValidationError) else {"purchased_at": "Use an ISO date (YYYY-MM-DD)."}
            return Response(details, status=400)
        return Response(PurchaseSerializer(purchase).data, status=201)


class StockMovementListView(generics.ListAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_stockmovement"
    serializer_class = StockMovementSerializer
    queryset = StockMovement.objects.select_related("stockrecord__product").all()


class LowStockView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_stockmovement"

    def get(self, request):
        records = get_model("partner", "StockRecord").objects.select_related("product").filter(
            low_stock_threshold__isnull=False, num_in_stock__isnull=False,
        ).order_by("num_in_stock")
        result = [{
            "stockrecord_id": record.pk,
            "product_id": record.product_id,
            "product": record.product.get_title(),
            "barcode": record.product.upc,
            "available": max(0, record.net_stock_level or 0),
            "minimum": record.low_stock_threshold,
            "status": "out_of_stock" if (record.net_stock_level or 0) <= 0 else "low_stock",
        } for record in records if (record.net_stock_level or 0) <= record.low_stock_threshold]
        return Response({"results": result, "count": len(result)})


class StockAdjustmentView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.add_stockmovement"

    def post(self, request):
        try:
            movement = adjust_stock(
                stockrecord_id=request.data.get("stockrecord_id"),
                quantity_delta=request.data.get("quantity_delta"),
                reason=request.data.get("movement_type"),
                created_by=request.user,
                note=request.data.get("note", ""),
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=400)
        return Response(StockMovementSerializer(movement).data, status=201)



class CashierShiftListCreateView(generics.ListCreateAPIView):
    serializer_class = CashierShiftSerializer
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_cashiershift"

    def get_queryset(self):
        user = self.request.user
        queryset = CashierShift.objects.select_related("cashier")
        if user.has_perm("mis.view_cashiershift") and not user.has_perm("mis.view_cashiershift_all"):
            return queryset.filter(cashier=user)
        return queryset

    def create(self, request, *args, **kwargs):
        if not request.user.has_perm("mis.add_cashiershift"):
            return Response({"detail": "You do not have permission to open a cashier shift."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CashierShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = open_cashier_shift(
                cashier=request.user,
                opening_cash=serializer.validated_data["opening_cash"],
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        return Response(CashierShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class CurrentCashierShiftView(generics.RetrieveAPIView):
    serializer_class = CashierShiftSerializer
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_cashiershift"

    def get_object(self):
        return get_object_or_404(
            CashierShift.objects.select_related("cashier"),
            cashier=self.request.user,
            status=CashierShift.STATUS_OPEN,
        )


class CashierShiftCloseView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.change_cashiershift"

    def post(self, request, pk):
        shift = get_object_or_404(CashierShift, pk=pk)
        if shift.cashier_id != request.user.pk and not request.user.has_perm("mis.change_cashiershift_all"):
            return Response({"detail": "You can only close your own cashier shift."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CashierShiftSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            closed = close_cashier_shift(
                shift_id=shift.pk,
                closing_cash=serializer.validated_data.get("closing_cash"),
                note=serializer.validated_data.get("note", ""),
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        return Response(CashierShiftSerializer(closed).data)

class DashboardSummaryView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_dashboard"

    def get(self, request):
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from apps.mis.models import Expense

        today = timezone.localdate()
        month_start = today.replace(day=1)
        sales = POSSale.objects.all()
        can_view_sales = request.user.has_perm("mis.view_possale")
        can_view_purchases = request.user.has_perm("mis.view_purchase")
        can_view_expenses = request.user.has_perm("mis.view_expense")
        can_view_all_sales = request.user.has_perm("mis.view_possale_all")
        if not can_view_all_sales:
            sales = sales.filter(cashier=request.user)
        today_sales = sales.filter(created_at__date=today)
        month_sales = sales.filter(created_at__date__gte=month_start)
        online_today = Order.objects.filter(date_placed__date=today) if can_view_sales and can_view_all_sales else Order.objects.none()
        online_month = Order.objects.filter(date_placed__date__gte=month_start) if can_view_sales and can_view_all_sales else Order.objects.none()
        stock_records = get_model("partner", "StockRecord").objects.select_related("product").filter(
            low_stock_threshold__isnull=False, num_in_stock__isnull=False,
        )
        low_stock = []
        low_stock_count = 0
        for row in stock_records.only("product__title", "partner_sku", "num_in_stock", "num_allocated", "low_stock_threshold").order_by("num_in_stock"):
            available = max(0, row.net_stock_level or 0)
            if available <= row.low_stock_threshold:
                low_stock_count += 1
                if len(low_stock) < 12:
                    low_stock.append({"product": row.product.title, "sku": row.partner_sku, "available": available, "threshold": row.low_stock_threshold})
        days = [today - timedelta(days=offset) for offset in reversed(range(7))]
        daily = []
        if can_view_sales:
            for day in days:
                amount = sales.filter(created_at__date=day).aggregate(value=Sum("total"))["value"] or Decimal("0.00")
                if can_view_all_sales:
                    amount += Order.objects.filter(date_placed__date=day).aggregate(value=Sum("total_incl_tax"))["value"] or Decimal("0.00")
                daily.append({"date": day.isoformat(), "sales": str(amount)})
        result = {"currency": settings.OSCAR_DEFAULT_CURRENCY}
        if request.user.has_perm("catalogue.view_product"):
            result["products"] = Product.objects.count()
        if request.user.has_perm("mis.view_supplier"):
            result["suppliers"] = Supplier.objects.filter(is_active=True).count()
        if can_view_sales:
            top_items = POSSaleItem.objects.all()
            if not can_view_all_sales:
                top_items = top_items.filter(sale__cashier=request.user)
            top_products = top_items.values("title").annotate(quantity=Sum("quantity"), revenue=Sum("line_total")).order_by("-quantity")[:5]
            payment_methods = sales.values("payment_method").annotate(count=Count("id"), amount=Sum("total")).order_by("payment_method")
            result.update({
                "today_sales": str((today_sales.aggregate(value=Sum("total"))["value"] or Decimal("0.00")) + (online_today.aggregate(value=Sum("total_incl_tax"))["value"] or Decimal("0.00"))),
                "month_sales": str((month_sales.aggregate(value=Sum("total"))["value"] or Decimal("0.00")) + (online_month.aggregate(value=Sum("total_incl_tax"))["value"] or Decimal("0.00"))),
                "today_transactions": today_sales.count() + online_today.count(),
                "month_transactions": month_sales.count() + online_month.count(),
                "daily_sales": daily, "top_products": list(top_products), "payment_methods": list(payment_methods),
            })
            outstanding = POSSale.objects.annotate(
                amount_paid=Coalesce(
                    Sum("payment_transactions__amount", filter=Q(payment_transactions__status=PaymentTransaction.STATUS_PAID)),
                    Decimal("0.00"),
                ),
            ).annotate(balance_due=F("total") - F("amount_paid")).filter(balance_due__gt=0)
            balance_amounts = list(outstanding.values_list("total", "amount_paid"))
            result["outstanding_balance_total"] = str(
                sum((total - paid for total, paid in balance_amounts), Decimal("0.00"))
            )
            result["outstanding_balance_count"] = len(balance_amounts)
            result["outstanding_balances"] = [{
                "invoice_number": sale.invoice_number,
                "customer_name": sale.customer_name or (sale.customer.get_full_name() if sale.customer_id else ""),
                "customer_phone": sale.customer_phone,
                "cashier": sale.cashier.get_full_name() or sale.cashier.email or sale.cashier.get_username(),
                "created_at": sale.created_at,
                "total": str(sale.total),
                "amount_paid": str(sale.amount_paid),
                "balance_due": str(sale.balance_due),
                "currency": sale.currency,
            } for sale in outstanding.select_related("cashier", "customer").order_by("-created_at")[:10]]
            if can_view_all_sales:
                result["total_orders"] = Order.objects.count()
                result["pending_orders"] = Order.objects.filter(status__iexact="Pending").count()
            recent = sales.select_related("cashier").prefetch_related("items").order_by("-created_at")[:10]
            result["recent_sales"] = [{
                "invoice_number": sale.invoice_number,
                "cashier": sale.cashier.get_full_name() or sale.cashier.email or sale.cashier.get_username(),
                "created_at": sale.created_at,
                "total": str(sale.total),
                "currency": sale.currency,
                "items": [{"title": item.title, "quantity": item.quantity} for item in sale.items.all()],
            } for sale in recent]
            cashier_rows = sales.filter(created_at__date=today).values(
                "cashier_id", "cashier__first_name", "cashier__last_name", "cashier__email"
            ).annotate(transactions=Count("id"), total=Sum("total")).order_by("-total")
            result["cashier_sales"] = [{
                "cashier": (row["cashier__first_name"] + (" " if row["cashier__last_name"] else "") + row["cashier__last_name"]) or row["cashier__email"],
                "transactions": row["transactions"],
                "units": POSSaleItem.objects.filter(sale__cashier_id=row["cashier_id"], sale__created_at__date=today).aggregate(value=Sum("quantity"))["value"] or 0,
                "total": str(row["total"] or Decimal("0.00")),
            } for row in cashier_rows]
        if request.user.has_perm("partner.view_stockrecord"):
            result["low_stock_products"] = low_stock_count
            result["low_stock"] = low_stock
        if request.user.has_perm("mis.change_possale"):
            pending = POSSaleCorrectionRequest.objects.filter(is_resolved=False).select_related("sale__cashier", "requested_by")[:20]
            result["correction_requests"] = POSSaleCorrectionRequestSerializer(pending, many=True).data
        if can_view_purchases:
            result["purchases_month"] = str(Purchase.objects.filter(purchased_at__gte=month_start).aggregate(value=Sum("total_cost"))["value"] or Decimal("0.00"))
        if can_view_expenses:
            result["expenses_month"] = str(Expense.objects.filter(spent_at__gte=month_start).aggregate(value=Sum("amount"))["value"] or Decimal("0.00"))
        return Response(result)



class FinancialReportView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_financialreport"

    def get(self, request):
        start_date = parse_date(request.query_params.get("start_date", "")) if request.query_params.get("start_date") else None
        end_date = parse_date(request.query_params.get("end_date", "")) if request.query_params.get("end_date") else None
        if request.query_params.get("start_date") and start_date is None:
            return Response({"detail": "start_date must use YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
        if request.query_params.get("end_date") and end_date is None:
            return Response({"detail": "end_date must use YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            report = financial_summary(start_date=start_date, end_date=end_date)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(report)


class POSSaleCorrectionRequestCreateView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"

    def post(self, request, invoice_number):
        sale = get_object_or_404(POSSale, invoice_number=invoice_number)
        if sale.cashier_id != request.user.pk and not request.user.has_perm("mis.view_possale_all"):
            return Response({"detail": "You can request a correction only for your own sale."}, status=status.HTTP_404_NOT_FOUND)
        serializer = POSSaleCorrectionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if POSSaleCorrectionRequest.objects.filter(sale=sale, is_resolved=False).exists():
            return Response({"detail": "A correction request is already open for this sale."}, status=status.HTTP_409_CONFLICT)
        correction_request = POSSaleCorrectionRequest.objects.create(
            sale=sale, requested_by=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(POSSaleCorrectionRequestSerializer(correction_request).data, status=status.HTTP_201_CREATED)


class POSSaleCorrectionCreateView(APIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.change_possale"

    def post(self, request, invoice_number):
        serializer = POSSaleCorrectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            correction = correct_pos_sale(
                invoice_number=invoice_number,
                processed_by=request.user,
                **serializer.validated_data,
            )
        except POSSale.DoesNotExist:
            return Response({"detail": "Sale invoice was not found."}, status=404)
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=400)
        return Response(POSSaleCorrectionSerializer(correction).data, status=201)
