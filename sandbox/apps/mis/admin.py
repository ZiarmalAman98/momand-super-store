from django.contrib import admin

from .models import Expense, PaymentTransaction, POSSale, POSSaleItem, POSSaleReturn, POSSaleReturnItem, Purchase, PurchaseItem, StockMovement, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "phone", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_name", "phone", "email")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("reference", "supplier", "purchased_at", "total_cost")
    list_filter = ("purchased_at", "supplier")
    search_fields = ("reference", "supplier__name")
    date_hierarchy = "purchased_at"
    readonly_fields = ("created_at", "created_by", "total_cost", "status")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("mis.view_purchase") or request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "category", "amount", "payment_method", "spent_at")
    list_filter = ("category", "spent_at")
    search_fields = ("description", "notes")
    date_hierarchy = "spent_at"
    readonly_fields = ("created_at", "created_by")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("mis.view_expense") or request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ("line_total",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(POSSale)
class POSSaleAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "cashier", "payment_method", "total", "created_at")
    list_filter = ("payment_method", "created_at")
    search_fields = ("invoice_number", "cashier__username", "cashier__email")
    readonly_fields = tuple(field.name for field in POSSale._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(POSSaleItem)
class POSSaleItemAdmin(admin.ModelAdmin):
    list_display = ("sale", "title", "sku", "quantity", "unit_price", "line_total")
    search_fields = ("sale__invoice_number", "title", "sku")
    readonly_fields = tuple(field.name for field in POSSaleItem._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(POSSaleReturn)
class POSSaleReturnAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "sale", "processed_by", "refund_method", "refund_total", "restocked", "created_at")
    list_filter = ("refund_method", "restocked", "created_at")
    search_fields = ("invoice_number", "sale__invoice_number", "reason")
    readonly_fields = tuple(field.name for field in POSSaleReturn._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(POSSaleReturnItem)
class POSSaleReturnItemAdmin(admin.ModelAdmin):
    list_display = ("sale_return", "sale_item", "quantity", "refund_amount")
    readonly_fields = tuple(field.name for field in POSSaleReturnItem._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("stockrecord", "movement_type", "quantity_delta", "reference", "created_by", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("stockrecord__product__title", "reference", "note")
    readonly_fields = tuple(field.name for field in StockMovement._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False


PurchaseAdmin.inlines = (PurchaseItemInline,)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_ref", "sale", "order", "method", "status", "amount", "refunded_amount", "created_at")
    list_filter = ("method", "status", "gateway", "created_at")
    search_fields = ("transaction_ref", "sale__invoice_number", "order__number", "gateway", "note")
    readonly_fields = tuple(field.name for field in PaymentTransaction._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
