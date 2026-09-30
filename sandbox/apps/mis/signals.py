from django.dispatch import receiver
from oscar.apps.order.signals import order_placed

from .models import StockMovement


@receiver(order_placed, dispatch_uid="momand_audit_online_order_stock")
def record_online_order_stock_movements(sender, order, user, **kwargs):
    """Audit Oscar's stock allocations for each successfully placed web order."""
    quantities = {}
    records = {}
    for line in order.lines.select_related("stockrecord"):
        if line.stockrecord_id:
            quantities[line.stockrecord_id] = quantities.get(line.stockrecord_id, 0) + line.quantity
            records[line.stockrecord_id] = line.stockrecord
    for stockrecord_id, quantity in quantities.items():
        record = records[stockrecord_id]
        record.refresh_from_db(fields=["num_in_stock", "num_allocated"])
        after = max(0, record.net_stock_level or 0)
        before = after + quantity
        StockMovement.objects.create(
            stockrecord=record,
            movement_type=StockMovement.TYPE_ONLINE_SALE,
            quantity_delta=-quantity,
            quantity_before=before,
            quantity_after=after,
            reference=f"WEB-{order.number}",
            created_by=user if user and user.is_authenticated else None,
        )
