from decimal import Decimal
from datetime import datetime, time

from django.conf import settings\nfrom django.db.models import Count, Sum
from django.utils import timezone

from apps.mis.models import Expense, PaymentTransaction, POSSale, POSSaleReturn, Purchase
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

    pos_gross = _money(pos_sales.aggregate(value=Sum("total"))["value"])
    pos_refunds = _money(pos_returns.aggregate(value=Sum("refund_total"))["value"])
    pos_net = pos_gross - pos_refunds
    online_gross = _money(online_orders.aggregate(value=Sum("total_incl_tax"))["value"])
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
    for row in paid.values("method").annotate(count=Count("id"), amount=Sum("amount")).order_by("method"):
        payment_breakdown.append({
            "method": row["method"],
            "count": row["count"],
            "amount": str(_money(row["amount"])),
        })

    cash_collected = _money(paid.filter(method=PaymentTransaction.METHOD_CASH).aggregate(value=Sum("amount"))["value"])
    cash_refunded = _money(refunded.filter(method=PaymentTransaction.METHOD_CASH).aggregate(value=Sum("refunded_amount"))["value"])

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "currency": getattr(settings, "OSCAR_DEFAULT_CURRENCY", "AFN"),
        "pos_sales": {"transactions": pos_sales.count(), "gross": str(pos_gross), "refunds": str(pos_refunds), "net": str(pos_net)},
        "online_sales": {"orders": online_orders.count(), "gross": str(online_gross)},
        "revenue": {"gross": str(pos_gross + online_gross), "refunds": str(pos_refunds), "net": str(pos_net + online_gross)},
        "purchases": {"transactions": purchases.count(), "total": str(purchase_total)},
        "expenses": {"transactions": expenses.count(), "total": str(expense_total)},
        "cash": {"collected": str(cash_collected), "refunded": str(cash_refunded), "net": str(cash_collected - cash_refunded)},
        "payment_breakdown": payment_breakdown,
        "accounting_status": "cogs_not_modeled",
        "accounting_note": "Gross profit and net profit are not calculated yet because historical cost-of-goods-sold is not modeled in the sale records.",
    }
