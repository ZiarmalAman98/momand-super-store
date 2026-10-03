from django.contrib.auth.decorators import permission_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from oscar.core.loading import get_model

from .models import Expense, Purchase

Order = get_model("order", "Order")
StockRecord = get_model("partner", "StockRecord")


@permission_required("mis.view_dashboard")
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    orders = Order.objects.all()
    today_orders = orders.filter(date_placed__date=today)
    month_orders = orders.filter(date_placed__date__gte=month_start)
    stock_records = StockRecord.objects.select_related("product")

    context = {
        "today": today,
        "today_order_count": today_orders.count(),
        "month_order_count": month_orders.count(),
        "month_revenue": month_orders.aggregate(total=Sum("total_incl_tax"))["total"] or 0,
        "month_purchase_cost": Purchase.objects.filter(
            purchased_at__gte=month_start
        ).aggregate(total=Sum("total_cost"))["total"] or 0,
        "month_expenses": Expense.objects.filter(
            spent_at__gte=month_start
        ).aggregate(total=Sum("amount"))["total"] or 0,
        "low_stock": stock_records.filter(num_in_stock__lte=5).order_by(
            "num_in_stock", "product__title"
        )[:8],
        "latest_orders": orders.order_by("-date_placed")[:8],
        "recent_expenses": Expense.objects.select_related("created_by")[:5],
        "low_stock_count": stock_records.filter(num_in_stock__lte=5).count(),
    }
    return render(request, "mis/dashboard.html", context)
