from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from oscar.core.loading import get_model

from .models import POSSale, POSSaleItem, POSSaleReturn, POSSaleReturnItem, Purchase, PurchaseItem, StockMovement

Product = get_model("catalogue", "Product")
StockRecord = get_model("partner", "StockRecord")
User = get_model("auth", "User")


def _decimal(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({label: "Enter a valid amount."})
    if not amount.is_finite() or amount < 0 or amount > Decimal("9999999999.99"):
        raise ValidationError({label: "Amount must be non-negative and fit the store's money limits."})
    try:
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValidationError({label: "Amount is outside the supported money range."})


def _quantity(value):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise ValidationError({"quantity": "Enter a whole-number quantity."})
    if quantity < 1 or quantity > 100000:
        raise ValidationError({"quantity": "Quantity must be between 1 and 100000."})
    return quantity


def _product_and_record(item):
    """Resolve one sellable product without locking.

    Stock rows are locked later in deterministic PK order. This is important
    when a transaction contains multiple products: locking in request order
    can otherwise create avoidable deadlocks between concurrent checkouts/POS
    sales.
    """
    product_id = item.get("product_id")
    barcode = str(item.get("barcode", "")).strip()
    if not product_id and not barcode:
        raise ValidationError({"items": "Each item needs a product_id or barcode."})
    if product_id:
        try:
            product_id = int(product_id)
            if product_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError({"items": "Product id must be a positive integer."})
    products = Product.objects.filter(
        Q(pk=product_id) if product_id else Q(upc=barcode)
    ).browsable()
    matches = list(products[:2])
    if not matches:
        raise ValidationError({"items": "A scanned product was not found or is inactive."})
    if len(matches) > 1:
        raise ValidationError({
            "items": "This barcode matches more than one product; resolve it in catalogue management."
        })
    product = matches[0]
    record = StockRecord.objects.filter(product=product).order_by("pk").first()
    if not record:
        raise ValidationError({"items": f"{product.get_title()} has no stock record."})
    return product, record


def _lock_stock_records(record_ids):
    """Lock stock rows in a deterministic order for the current transaction."""
    locked = {
        record.pk: record
        for record in StockRecord.objects.select_for_update().filter(
            pk__in=record_ids
        ).order_by("pk")
    }
    missing = set(record_ids) - set(locked)
    if missing:
        raise ValidationError({"items": "One or more stock records no longer exist."})
    return locked


@transaction.atomic
def create_pos_sale(*, cashier, items, payment_method, amount_tendered, customer_id=None):
    if not isinstance(items, list) or not items:
        raise ValidationError({"items": "Add at least one product to the sale."})
    if any(not isinstance(item, dict) for item in items):
        raise ValidationError({"items": "Each sale item must be an object."})
    if payment_method not in dict(POSSale.PAYMENT_CHOICES):
        raise ValidationError({"payment_method": "Choose cash, card, or bank transfer."})
    customer = None
    if customer_id:
        try:
            customer = User.objects.get(pk=customer_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError({"customer_id": "Customer account was not found."})

    prepared_by_record = {}
    currency = None
    subtotal = Decimal("0.00")
    for item in items:
        product, record = _product_and_record(item)
        quantity = _quantity(item.get("quantity"))
        if record.num_in_stock is None:
            raise ValidationError({"items": f"Stock tracking is required before selling {product.get_title()}."})
        price = _decimal(record.price, "price")
        if currency and currency != record.price_currency:
            raise ValidationError({"items": "All sale products must use the same currency."})
        currency = record.price_currency
        line_total = price * quantity
        subtotal += line_total
        if record.pk in prepared_by_record:
            prepared_by_record[record.pk][2] += quantity
            prepared_by_record[record.pk][4] += line_total
        else:
            prepared_by_record[record.pk] = [product, record, quantity, price, line_total]

    prepared = list(prepared_by_record.values())
    locked_records = _lock_stock_records([record.pk for _product, record, _quantity, _price, _line_total in prepared])
    prepared = [
        [product, locked_records[record.pk], quantity, price, line_total]
        for product, record, quantity, price, line_total in prepared
    ]
    for product, record, quantity, _price, _line_total in prepared:
        available = max(0, record.net_stock_level or 0)
        if quantity > available:
            raise ValidationError({"items": f"Only {available} units of {product.get_title()} are available."})
    if subtotal > Decimal("9999999999999.99"):
        raise ValidationError({"items": "Sale total exceeds the supported currency range."})

    try:
        tax_rate = Decimal(str(getattr(settings, "STORE_TAX_RATE", "0")))
    except InvalidOperation:
        raise ValidationError({"tax": "STORE_TAX_RATE must be a decimal fraction."})
    if tax_rate < 0 or tax_rate > 1:
        raise ValidationError({"tax": "STORE_TAX_RATE must be between 0 and 1."})
    line_taxes = {record.pk: (price * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for _product, record, _quantity, price, _line_total in prepared}
    tax = sum((line_taxes[record.pk] * quantity for _product, record, quantity, _price, _line_total in prepared), Decimal("0.00"))
    total = subtotal + tax
    tendered = _decimal(amount_tendered, "amount_tendered")
    if tendered < total:
        raise ValidationError({"amount_tendered": f"Payment must be at least {total}."})
    change = (tendered - total) if payment_method == POSSale.PAYMENT_CASH else Decimal("0.00")
    if payment_method != POSSale.PAYMENT_CASH and tendered != total:
        raise ValidationError({"amount_tendered": "Non-cash payment must match the sale total."})

    sale = POSSale.objects.create(
        cashier=cashier, customer=customer, currency=currency,
        subtotal=subtotal, tax=tax, total=total,
        payment_method=payment_method, amount_tendered=tendered, change_due=change,
    )
    for product, record, quantity, price, line_total in prepared:
        before = max(0, record.net_stock_level or 0)
        if record.num_in_stock is None or record.num_in_stock < (record.num_allocated or 0) + quantity:
            raise ValidationError({"items": f"Only {before} units of {product.get_title()} are available."})
        record.num_in_stock -= quantity
        record.save(update_fields=["num_in_stock"])
        POSSaleItem.objects.create(
            sale=sale, product=product, stockrecord=record,
            title=product.get_title(), sku=product.upc or "", quantity=quantity,
            unit_price=price, unit_tax=line_taxes[record.pk], line_total=line_total,
        )
        StockMovement.objects.create(
            stockrecord=record, movement_type=StockMovement.TYPE_POS_SALE,
            quantity_delta=-quantity, quantity_before=before,
            quantity_after=max(0, record.net_stock_level or 0),
            reference=sale.invoice_number, created_by=cashier,
        )
    return sale


@transaction.atomic
def process_pos_return(*, invoice_number, processed_by, items, refund_method, reason, restocked=True):
    if not isinstance(items, list) or not items:
        raise ValidationError({"items": "Select at least one sold item to return."})
    if any(not isinstance(item, dict) for item in items):
        raise ValidationError({"items": "Each return line must be an object."})
    if refund_method not in dict(POSSale.PAYMENT_CHOICES):
        raise ValidationError({"refund_method": "Choose cash, card, or bank transfer."})
    reason = str(reason).strip()
    if not reason or len(reason) > 240:
        raise ValidationError({"reason": "Enter a return reason up to 240 characters."})
    if not isinstance(restocked, bool):
        raise ValidationError({"restocked": "Choose whether returned items can be sold again."})
    try:
        sale = POSSale.objects.select_for_update().get(invoice_number=invoice_number)
    except POSSale.DoesNotExist:
        raise ValidationError({"invoice_number": "POS sale was not found."})

    requested = {}
    for item in items:
        try:
            line_id = int(item.get("sale_item_id"))
        except (TypeError, ValueError):
            raise ValidationError({"items": "Each return line needs a valid sale_item_id."})
        requested[line_id] = requested.get(line_id, 0) + _quantity(item.get("quantity"))
    lines = list(POSSaleItem.objects.select_for_update().filter(sale=sale, pk__in=requested).order_by("stockrecord_id", "pk"))
    if len(lines) != len(requested):
        raise ValidationError({"items": "A selected item does not belong to this sale."})
    locked_return_records = _lock_stock_records(
        sorted({line.stockrecord_id for line in lines})
    )
    refund_total = Decimal("0.00")
    for line in lines:
        already_returned = line.return_items.aggregate(quantity=Sum("quantity"))["quantity"] or 0
        quantity = requested[line.pk]
        if already_returned + quantity > line.quantity:
            remaining = line.quantity - already_returned
            raise ValidationError({"items": f"Only {remaining} units of {line.title} remain eligible for return."})
        refund_total += (line.unit_price + line.unit_tax) * quantity
    previously_refunded = sale.returns.aggregate(value=Sum("refund_total"))["value"] or Decimal("0.00")
    if previously_refunded + refund_total > sale.total:
        raise ValidationError({"items": "This return would refund more than the original sale total."})

    sale_return = POSSaleReturn.objects.create(
        sale=sale, processed_by=processed_by, refund_method=refund_method,
        refund_total=refund_total, reason=reason, restocked=restocked,
    )
    for line in lines:
        quantity = requested[line.pk]
        amount = (line.unit_price + line.unit_tax) * quantity
        POSSaleReturnItem.objects.create(
            sale_return=sale_return, sale_item=line,
            quantity=quantity, refund_amount=amount,
        )
        if restocked:
            record = locked_return_records[line.stockrecord_id]
            before = max(0, record.net_stock_level or 0) if record.num_in_stock is not None else 0
            record.num_in_stock = (record.num_in_stock or 0) + quantity
            record.save(update_fields=["num_in_stock"])
            StockMovement.objects.create(
                stockrecord=record, movement_type=StockMovement.TYPE_RETURN,
                quantity_delta=quantity, quantity_before=before,
                quantity_after=max(0, record.net_stock_level or 0),
                reference=sale_return.invoice_number, note=f"Return against {sale.invoice_number}",
                created_by=processed_by,
            )
    return sale_return


@transaction.atomic
def receive_purchase(*, supplier, reference, purchased_at, items, created_by, notes=""):
    if not isinstance(items, list) or not items:
        raise ValidationError({"items": "Add at least one product to the purchase."})
    if any(not isinstance(item, dict) for item in items):
        raise ValidationError({"items": "Each purchase item must be an object."})
    if Purchase.objects.filter(reference=reference).exists():
        raise ValidationError({"reference": "This supplier invoice reference already exists."})
    prepared = []
    total = Decimal("0.00")
    currency = None
    for item in items:
        product, record = _product_and_record(item)
        if currency and currency != record.price_currency:
            raise ValidationError({"items": "All purchase products must use the same currency."})
        currency = record.price_currency
        quantity = _quantity(item.get("quantity"))
        unit_cost = _decimal(item.get("unit_cost"), "unit_cost")
        line_total = unit_cost * quantity
        total += line_total
        prepared.append((product, record, quantity, unit_cost, line_total))
    if total > Decimal("9999999999999.99"):
        raise ValidationError({"items": "Purchase total exceeds the supported currency range."})
    locked_records = _lock_stock_records([record.pk for _product, record, _quantity, _unit_cost, _line_total in prepared])
    prepared = [
        (product, locked_records[record.pk], quantity, unit_cost, line_total)
        for product, record, quantity, unit_cost, line_total in prepared
    ]
    purchase = Purchase.objects.create(
        supplier=supplier, reference=reference, purchased_at=purchased_at,
        currency=currency, total_cost=total, status=Purchase.STATUS_RECEIVED,
        notes=notes, created_by=created_by,
    )
    for product, record, quantity, unit_cost, line_total in prepared:
        before = max(0, record.net_stock_level or 0) if record.num_in_stock is not None else 0
        record.num_in_stock = (record.num_in_stock or 0) + quantity
        record.save(update_fields=["num_in_stock"])
        PurchaseItem.objects.create(
            purchase=purchase, product=product, stockrecord=record,
            quantity=quantity, unit_cost=unit_cost, line_total=line_total,
        )
        StockMovement.objects.create(
            stockrecord=record, movement_type=StockMovement.TYPE_PURCHASE,
            quantity_delta=quantity, quantity_before=before,
            quantity_after=max(0, record.net_stock_level or 0),
            reference=purchase.reference, created_by=created_by,
        )
    return purchase


@transaction.atomic
def adjust_stock(*, stockrecord_id, quantity_delta, reason, created_by, note=""):
    try:
        delta = int(quantity_delta)
    except (TypeError, ValueError):
        raise ValidationError({"quantity_delta": "Enter a whole-number stock adjustment."})
    if delta == 0 or abs(delta) > 100000:
        raise ValidationError({"quantity_delta": "Adjustment must be between -100000 and 100000, excluding zero."})
    allowed_reasons = {StockMovement.TYPE_DAMAGE, StockMovement.TYPE_ADJUSTMENT, StockMovement.TYPE_RETURN, StockMovement.TYPE_OPENING}
    if reason not in allowed_reasons:
        raise ValidationError({"movement_type": "Choose a supported adjustment reason."})
    if (reason == StockMovement.TYPE_DAMAGE and delta > 0) or (reason in (StockMovement.TYPE_RETURN, StockMovement.TYPE_OPENING) and delta < 0):
        raise ValidationError({"quantity_delta": "Damage must decrease stock; returns and opening stock must increase it."})
    try:
        record = StockRecord.objects.select_for_update().get(pk=stockrecord_id)
    except StockRecord.DoesNotExist:
        raise ValidationError({"stockrecord_id": "Stock record was not found."})
    before = max(0, record.net_stock_level or 0) if record.num_in_stock is not None else 0
    after_physical = (record.num_in_stock or 0) + delta
    allocated = record.num_allocated or 0
    if after_physical < allocated or after_physical < 0:
        raise ValidationError({"quantity_delta": "Adjustment cannot reduce stock below quantities reserved for orders."})
    record.num_in_stock = after_physical
    record.save(update_fields=["num_in_stock"])
    after = max(0, record.net_stock_level or 0)
    return StockMovement.objects.create(
        stockrecord=record, movement_type=reason, quantity_delta=delta,
        quantity_before=before, quantity_after=after,
        note=str(note)[:240], created_by=created_by,
    )
