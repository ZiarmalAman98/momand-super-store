from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import serializers as drf_serializers

from oscar.core.loading import get_model
from oscar.apps.shipping.methods import Free
from oscar.apps.checkout.calculators import OrderTotalCalculator
from oscar.apps.order.utils import OrderCreator

from .permissions import HasAnyMISPermission, StaffWriteCustomerReadOnly
from .serializers import (
    BasketLineSerializer,
    CategorySerializer,
    ContactMessageSerializer,
    RegistrationSerializer,
    OrderSerializer,
    POSSaleSerializer,
    ProductSerializer,
    PurchaseSerializer,
    StockMovementSerializer,
    SupplierSerializer,
    ExpenseSerializer,
    POSSaleReturnSerializer,
    POSSaleReturnCreateSerializer,
)
from .services import add_to_basket, get_session_basket
from .permissions import HasMISPermission
from apps.mis.models import Expense, POSSale, POSSaleItem, POSSaleReturn, Purchase, StockMovement, Supplier
from apps.mis.services import adjust_stock, create_pos_sale, process_pos_return, receive_purchase

Category = get_model("catalogue", "Category")
Product = get_model("catalogue", "Product")
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
            queryset = queryset.filter(stockrecords__num_in_stock__gt=0)
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
        return Response({
            "name": settings.OSCAR_SHOP_NAME,
            "currency": settings.OSCAR_DEFAULT_CURRENCY,
            "tax_rate": str(settings.STORE_TAX_RATE),
            "phone": settings.STORE_PHONE,
            "email": settings.STORE_EMAIL,
            "address": settings.STORE_ADDRESS,
        })


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
        })


class CustomerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "number"
    lookup_url_kwarg = "number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("lines").order_by("-date_placed")


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
        method = data.get("payment_method", "cod")
        if method != "cod":
            return Response({"payment_method": "Cash on delivery is the only configured checkout payment method."}, status=400)
        try:
            country = Country.objects.get(iso_3166_1_a2=str(data["country"]).upper())
        except Country.DoesNotExist:
            return Response({"country": "Choose a supported delivery country."}, status=400)

        try:
            with transaction.atomic():
                for line in basket.all_lines():
                    record = line.stockrecord.__class__.objects.select_for_update().get(pk=line.stockrecord_id)
                    if record.num_in_stock is not None and record.net_stock_level < line.quantity:
                        return Response({"detail": f"Insufficient stock for {line.product.get_title()}."}, status=400)
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
                basket.submit()
        except (ObjectDoesNotExist, ValueError) as exc:
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
    queryset = POSSale.objects.prefetch_related("items__return_items").select_related("cashier")
    filterset_fields = ("payment_method", "cashier")
    ordering_fields = ("created_at", "total")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.groups.filter(name="Cashier").exists() and not self.request.user.is_superuser:
            queryset = queryset.filter(cashier=self.request.user)
        return queryset


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
                customer_id=request.data.get("customer_id"),
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=400)
        return Response(POSSaleSerializer(sale).data, status=201)


class POSSaleDetailView(generics.RetrieveAPIView):
    permission_classes = (HasMISPermission,)
    required_permission = "mis.view_possale"
    serializer_class = POSSaleSerializer
    queryset = POSSale.objects.prefetch_related("items__return_items").select_related("cashier")
    lookup_field = "invoice_number"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.groups.filter(name="Cashier").exists() and not self.request.user.is_superuser:
            queryset = queryset.filter(cashier=self.request.user)
        return queryset


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


class DashboardSummaryView(APIView):
    permission_classes = (HasAnyMISPermission,)
    required_permissions = ("mis.view_possale", "mis.view_purchase", "mis.view_expense", "mis.view_stockmovement")

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
        is_cashier = request.user.groups.filter(name="Cashier").exists() and not request.user.is_superuser
        if is_cashier:
            sales = sales.filter(cashier=request.user)
        today_sales = sales.filter(created_at__date=today)
        month_sales = sales.filter(created_at__date__gte=month_start)
        online_today = Order.objects.filter(date_placed__date=today) if can_view_sales and not is_cashier else Order.objects.none()
        online_month = Order.objects.filter(date_placed__date__gte=month_start) if can_view_sales and not is_cashier else Order.objects.none()
        stock_records = get_model("partner", "StockRecord").objects.filter(
            low_stock_threshold__isnull=False, num_in_stock__isnull=False,
        )
        low_stock = [row for row in stock_records.only("num_in_stock", "num_allocated", "low_stock_threshold") if max(0, row.net_stock_level or 0) <= row.low_stock_threshold]
        days = [today - timedelta(days=offset) for offset in reversed(range(7))]
        daily = []
        if can_view_sales:
            for day in days:
                amount = sales.filter(created_at__date=day).aggregate(value=Sum("total"))["value"] or Decimal("0.00")
                if not is_cashier:
                    amount += Order.objects.filter(date_placed__date=day).aggregate(value=Sum("total_incl_tax"))["value"] or Decimal("0.00")
                daily.append({"date": day.isoformat(), "sales": str(amount)})
        result = {
            "currency": settings.OSCAR_DEFAULT_CURRENCY,
            "products": Product.objects.count(),
            "low_stock_products": len(low_stock),
            "suppliers": Supplier.objects.filter(is_active=True).count(),
        }
        if can_view_sales:
            top_items = POSSaleItem.objects.all()
            if is_cashier:
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
            if not is_cashier:
                result["total_orders"] = Order.objects.count()
                result["pending_orders"] = Order.objects.filter(status__iexact="Pending").count()
        if can_view_purchases:
            result["purchases_month"] = str(Purchase.objects.filter(purchased_at__gte=month_start).aggregate(value=Sum("total_cost"))["value"] or Decimal("0.00"))
        if can_view_expenses:
            result["expenses_month"] = str(Expense.objects.filter(spent_at__gte=month_start).aggregate(value=Sum("amount"))["value"] or Decimal("0.00"))
        return Response(result)

