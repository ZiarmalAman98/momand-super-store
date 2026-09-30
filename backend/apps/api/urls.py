from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth_views import (
    ConfirmPasswordResetView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    PasswordResetRequestView,
)
from .views import (
    BasketItemView,
    BasketView,
    CategoryViewSet,
    ContactMessageCreateView,
    CheckoutView,
    CurrentUserView,
    CustomerOrderViewSet,
    ProductViewSet,
    RegisterView,
    POSProductSearchView,
    POSSaleCreateView,
    POSSaleDetailView,
    POSSaleListView,
    PurchaseListView,
    PurchaseReceiveView,
    StockMovementListView,
    SupplierViewSet,
    LowStockView,
    StockAdjustmentView,
    StoreConfigView,
    CountryListView,
    DashboardSummaryView,
    ExpenseViewSet,
    PaymentTransactionListView,
    POSSaleReturnCreateView,
    POSSaleReturnListView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="api-product")
router.register("categories", CategoryViewSet, basename="api-category")
router.register("orders", CustomerOrderViewSet, basename="api-order")
router.register("suppliers", SupplierViewSet, basename="api-supplier")
router.register("expenses", ExpenseViewSet, basename="api-expense")

urlpatterns = [
    path("", include(router.urls)),
    path("config/", StoreConfigView.as_view(), name="api-store-config"),
    path("reports/dashboard/", DashboardSummaryView.as_view(), name="api-dashboard-summary"),
    path("countries/", CountryListView.as_view(), name="api-country-list"),
    path("cart/", BasketView.as_view(), name="api-cart"),
    path("checkout/", CheckoutView.as_view(), name="api-checkout"),
    path("pos/products/", POSProductSearchView.as_view(), name="api-pos-products"),
    path("pos/sales/", POSSaleListView.as_view(), name="api-pos-sales"),
    path("pos/sales/create/", POSSaleCreateView.as_view(), name="api-pos-sale-create"),
    path("pos/sales/<str:invoice_number>/", POSSaleDetailView.as_view(), name="api-pos-sale-detail"),
    path("pos/sales/<str:invoice_number>/returns/", POSSaleReturnCreateView.as_view(), name="api-pos-sale-return"),
    path("pos/returns/", POSSaleReturnListView.as_view(), name="api-pos-returns"),
    path("payments/transactions/", PaymentTransactionListView.as_view(), name="api-payment-transactions"),
    path("purchases/", PurchaseListView.as_view(), name="api-purchases"),
    path("purchases/receive/", PurchaseReceiveView.as_view(), name="api-purchase-receive"),
    path("inventory/movements/", StockMovementListView.as_view(), name="api-stock-movements"),
    path("inventory/low-stock/", LowStockView.as_view(), name="api-low-stock"),
    path("inventory/adjust/", StockAdjustmentView.as_view(), name="api-stock-adjust"),
    path("cart/items/<int:line_id>/", BasketItemView.as_view(), name="api-cart-item"),
    path("contact/", ContactMessageCreateView.as_view(), name="api-contact"),
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="api-password-reset"),
    path("auth/password-reset/confirm/", ConfirmPasswordResetView.as_view(), name="api-password-reset-confirm"),
    path("auth/token/", CookieTokenObtainPairView.as_view(), name="api-token-obtain"),
    path("auth/me/", CurrentUserView.as_view(), name="api-me"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
]
