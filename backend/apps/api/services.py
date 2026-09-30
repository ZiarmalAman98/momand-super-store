from django.core.exceptions import ObjectDoesNotExist
from oscar.core.loading import get_model

Product = get_model("catalogue", "Product")


def get_session_basket(request):
    """Return Oscar's session basket attached by BasketMiddleware."""
    try:
        return request.basket
    except ObjectDoesNotExist:
        return None


def add_to_basket(basket, product, quantity):
    record = product.stockrecords.order_by("pk").first()
    if not record:
        raise ValueError("This product is not currently available.")

    existing_quantity = sum(
        line.quantity for line in basket.all_lines() if line.product_id == product.pk
    )
    available = record.net_stock_level if record.num_in_stock is not None else None
    if available is not None and existing_quantity + quantity > available:
        raise ValueError("There is not enough stock for the requested quantity.")

    return basket.add_product(product, quantity=quantity)
