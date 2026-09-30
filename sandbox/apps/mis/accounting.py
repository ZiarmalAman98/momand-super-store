from decimal import Decimal
from datetime import datetime, time

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from apps.mis.models import (
    Expense,
    OnlineOrderCost,
    PaymentTransaction,
    POSSale,
    POSSaleReturn,
    POSSaleReturnItem,
    Purchase,
)
from oscar.core.loading import get_model

Order = get_model("order", "Order")


def _money(value):
    return value or Decimal("0.00")


def _date_range(start_date=None, end_date=None):
    today = timezone.localdate()
    if not start_date:
        start_date = today
    if not end_date:
        end_date = start_date
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
    return start_date, end_date, start_dt, end_dt


def financial_summary(*, start_date=None, end_date=None):
    start_date, end_date, start_dt, end_dt = _date_range(start_date, end_date)

    pos_sales = POSSale.objects.filter(created_at__range=(start_dt, end_dt))
    pos_returns = POSSaleReturn.objects.filter(created_at__range=(start_dt, end_dt))
    online_orders = Order.objects.filter(date_placed__range=(start_dt, end_dt))
    purchases = Purchase.objects.filter(
        purchased_at__gte=start_date,
        purchased_at__lte=end_date,
        status=Purchase.STATUS_RECEIVED,
    )
    expenses = Expense.objects.filter(spent_at__gte=start_date, spent_at__lte=end_date)

    # Revenue is reported before sales tax because tax collected is a liability,
    # not store revenue. Refunds are reduced by their pre-tax merchandise value.
    pos_revenue = _money(pos_sales.aggregate(value=Sum("subtotal"))["value"])
    pos_refund_revenue = _money(
        POSSaleReturnItem.objects.filter(
            sale_return__created_at__range=(start_dt, end_dt)
        ).aggregate(value=Sum("sale_item__unit_price"))["value"]
    )
    # The aggregate above is per unit, so use an explicit quantity-weighted
    # calculation for exact historical return revenue.
    pos_refund_revenue = Decimal("0.00")
    for row in POSSaleReturnItem.objects.filter(
        sale_return__created_at__range=(start_dt, end_dt)
    ).values("sale_item__unit_price", "quantity"):
        pos_refund_revenue += (
            row["sale_item__unit_price"] or Decimal("0.00")
        ) * row["quantity"]
    pos_net_revenue = pos_revenue - pos_refund_revenue

    online_revenue = _money(
        online_orders.aggregate(value=Sum("total_excl_tax"))["value"]
    )

    pos_cogs = _money(
        pos_sales.items.aggregate(value=Sum("items__cost_total"))["value"]
    ) if False else Decimal("0.00")
    # Django cannot traverse the reverse relation through a QuerySet alias
    # reliably across all supported Oscar configurations, so aggregate directly.
    from apps.mis.models import POSSaleItem
    pos_cogs = _money(
        POSSaleItem.objects.filter(
            sale__created_at__range=(start_dt, end_dt)
        ).aggregate(value=Sum("cost_total"))["value"]
    )
    returned_cogs = _money(
        POSSaleReturnItem.objects.filter(
            sale_return__created_at__range=(start_dt, end_dt),
            sale_return__restocked=True,
        ).aggregate(value=Sum("cost_total"))["value"]
    )
    online_cogs = _money(
        OnlineOrderCost.objects.filter(
            order__date_placed__range=(start_dt, end_dt)
        ).aggregate(value=Sum("cost_total"))["value"]
    )
    cogs = pos_cogs - returned_cogs + online_cogs

    purchase_total = _money(purchases.aggregate(value=Sum("total_cost"))["value"])
    expense_total = _money(expenses.aggregate(value=Sum("amount"))["value"])

    paid = PaymentTransaction.objects.filter(
        created_at__range=(start_dt, end_dt),
        status=PaymentTransaction.STATUS_PAID,
    )
    refunded = PaymentTransaction.objects.filter(
        created_at__range=(start_dt, end_dt),
        status=PaymentTransaction.STATUS_REFUNDED,
    )
    payment_breakdown = []
    for row in paid.values("method").annotate(
        count=Count("id"), amount=Sum("amount")
    ).order_by("method"):
        payment_breakdown.append({
            "method": row["method"],
            "count": row["count"],
            "amount": str(_money(row["amount"])),
        })

    cash_collected = _money(
        paid.filter(method=PaymentTransaction.METHOD_CASH)
        .aggregate(value=Sum("amount"))["value"]
    )
    cash_refunded = _money(
        refunded.filter(method=PaymentTransaction.METHOD_CASH)
        .aggregate(value=Sum("refunded_amount"))["value"]
    )

    missing_pos_cost_lines = POSSaleItem.objects.filter(
        sale__created_at__range=(start_dt, end_dt),
        unit_cost__isnull=True,
    ).count()
    gross_profit = pos_net_revenue + online_revenue - cogs
    net_profit = gross_profit - expense_total

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "currency": getattr(settings, "OSCAR_DEFAULT_CURRENCY", "AFN"),
        "pos_sales": {
            "transactions": pos_sales.count(),
            "gross": str(_money(pos_sales.aggregate(value=Sum("total"))["value"])),
            "gross_ex_tax": str(pos_revenue),
            "refunds": str(_money(pos_returns.aggregate(value=Sum("refund_total"))["value"])),
            "refunds_ex_tax": str(pos_refund_revenue),
            "net": str(_money(pos_sales.aggregate(value=Sum("total"))["value"]) - _money(pos_returns.aggregate(value=Sum("refund_total"))["value"])),
            "net_ex_tax": str(pos_net_revenue),
        },
        "online_sales": {
            "orders": online_orders.count(),
            "gross": str(_money(online_orders.aggregate(value=Sum("total_incl_tax"))["value"])),
            "gross_ex_tax": str(online_revenue),
        },
        "revenue": {
            "gross_including_tax": str(
                _money(pos_sales.aggregate(value=Sum("total"))["value"])
                + _money(online_orders.aggregate(value=Sum("total_incl_tax"))["value"])
            ),
            "net_ex_tax": str(pos_net_revenue + online_revenue),
        },
        "cogs": {
            "pos": str(pos_cogs),
            "returned_restocked": str(returned_cogs),
            "online": str(online_cogs),
            "net": str(cogs),
            "missing_pos_cost_lines": missing_pos_cost_lines,
        },
        "profit": {
            "gross": str(gross_profit),
            "net": str(net_profit),
            "formula": "net revenue excluding tax - COGS - operating expenses",
        },
        "purchases": {
            "transactions": purchases.count(),
            "total": str(purchase_total),
        },
        "expenses": {
            "transactions": expenses.count(),
            "total": str(expense_total),
        },
        "cash": {
            "collected": str(cash_collected),
            "refunded": str(cash_refunded),
            "net": str(cash_collected - cash_refunded),
        },
        "payment_breakdown": payment_breakdown,
        "accounting_status": (
            "historical_cost_data_required"
            if missing_pos_cost_lines
            else "cogs_modeled"
        ),
        "accounting_note": (
            "New POS and online sales snapshot inventory cost at sale time. "
            "Historical POS lines without a stored unit cost are excluded from "
            "COGS and must be reconciled before relying on profit for those dates."
            if missing_pos_cost_lines
            else "COGS uses sale-time inventory cost snapshots and weighted-average stock cost."
        ),
    }
