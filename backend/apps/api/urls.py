from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .access_views import AccessView, UserManagementView
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
    FinancialReportView,
    ExpenseViewSet,
    PaymentTransactionListView,
    CashierShiftListCreateView,
    CurrentCashierShiftView,
    CashierShiftCloseView,
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
    path("auth/access/", AccessView.as_view(), name="api-auth-access"),
    path("admin/users/", UserManagementView.as_view(), name="api-admin-users"),
    path("admin/users/<int:pk>/", UserManagementView.as_view(), name="api-admin-user-detail"),
    path("reports/dashboard/", DashboardSummaryView.as_view(), name="api-dashboard-summary"),
    path("reports/financial/", FinancialReportView.as_view(), name="api-financial-report"),
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
    path("pos/shifts/", CashierShiftListCreateView.as_view(), name="api-cashier-shifts"),
    path("pos/shifts/current/", CurrentCashierShiftView.as_view(), name="api-current-cashier-shift"),
    path("pos/shifts/<int:pk>/close/", CashierShiftCloseView.as_view(), name="api-cashier-shift-close"),
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
