from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import POSSale, POSSaleItem, PaymentTransaction, StockMovement
from .sale_corrections import POSSaleCorrection, POSSaleCorrectionItem


@transaction.atomic
def correct_pos_sale(*, invoice_number, processed_by, items, reason):
    sale = POSSale.objects.select_for_update().get(invoice_number=invoice_number)
    sale_items = {item.id: item for item in sale.items.select_for_update().select_related("stockrecord", "product")}
    if not items:
        raise ValidationError({"items": "Select at least one sale item to correct."})
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "A correction reason is required."})

    normalized = []
    for row in items:
        try:
            item_id = int(row["sale_item_id"])
            corrected_quantity = int(row["corrected_quantity"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError({"items": "Invalid sale correction item."})
        sale_item = sale_items.get(item_id)
        if not sale_item:
            raise ValidationError({"items": "The selected item does not belong to this invoice."})
        if corrected_quantity < 1 or corrected_quantity > sale_item.quantity:
            raise ValidationError({"items": f"Corrected quantity for {sale_item.title} must be between 1 and {sale_item.quantity}."})
        if corrected_quantity == sale_item.quantity:
            continue
        normalized.append((sale_item, corrected_quantity))

    if not normalized:
        raise ValidationError({"items": "The corrected quantity must be lower than the current quantity."})

    original_total = sale.total
    for sale_item, corrected_quantity in normalized:
        delta = sale_item.quantity - corrected_quantity
        stockrecord = sale_item.stockrecord
        stockrecord = type(stockrecord).objects.select_for_update().get(pk=stockrecord.pk)
        if stockrecord.num_in_stock is not None:
            before = max(0, stockrecord.net_stock_level or 0)
            stockrecord.num_in_stock += delta
            stockrecord.save(update_fields=["num_in_stock"])
            StockMovement.objects.create(
                stockrecord=stockrecord,
                movement_type=StockMovement.TYPE_ADJUSTMENT,
                quantity_delta=delta,
                quantity_before=before,
                quantity_after=max(0, stockrecord.net_stock_level or 0),
                reference=sale.invoice_number,
                note=f"Sale correction: {sale_item.title}; {sale_item.quantity} -> {corrected_quantity}",
                created_by=processed_by,
            )
        sale_item.quantity = corrected_quantity
        sale_item.line_total = (sale_item.unit_price + sale_item.unit_tax) * corrected_quantity
        sale_item.cost_total = (sale_item.unit_cost or Decimal("0.00")) * corrected_quantity
        sale_item.save(update_fields=["quantity", "line_total", "cost_total"])

    current_items = list(sale.items.all())
    sale.subtotal = sum((item.unit_price * item.quantity for item in current_items), Decimal("0.00"))
    sale.tax = sum((item.unit_tax * item.quantity for item in current_items), Decimal("0.00"))
    sale.total = max(Decimal("0.00"), sale.subtotal - sale.discount + sale.tax)
    sale.change_due = max(Decimal("0.00"), sale.amount_tendered - sale.total)
    sale.save(update_fields=["subtotal", "tax", "total", "change_due"])

    payment = sale.payment_transactions.filter(status=PaymentTransaction.STATUS_PAID).order_by("created_at", "id").first()
    if payment:
        old_amount = payment.amount
        payment.amount = sale.total
        payment.metadata = {**(payment.metadata or {}), "sale_correction": {"original_amount": str(old_amount), "corrected_amount": str(sale.total), "difference": str(old_amount - sale.total)}}
        payment.note = f"Adjusted by sale correction {sale.invoice_number}"
        payment.save(update_fields=["amount", "metadata", "note"])

    correction = POSSaleCorrection.objects.create(
        sale=sale, processed_by=processed_by, reason=reason,
        original_total=original_total, corrected_total=sale.total,
        difference=original_total - sale.total,
    )
    for sale_item, corrected_quantity in normalized:
        POSSaleCorrectionItem.objects.create(
            correction=correction, sale_item=sale_item,
            original_quantity=corrected_quantity + (sale_item.quantity - corrected_quantity),
            corrected_quantity=corrected_quantity,
            quantity_delta=corrected_quantity - (corrected_quantity + (sale_item.quantity - corrected_quantity)),
        )
    return correction
