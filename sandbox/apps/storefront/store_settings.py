from decimal import Decimal

from django.conf import settings
from django.db import models


class StoreSettings(models.Model):
    PAYMENT_METHODS = {
        "cod": "Cash on delivery",
        "bank_transfer": "Bank transfer",
    }

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    store_name = models.CharField(max_length=160, default="Momand Super Store")
    tagline = models.CharField(max_length=240, blank=True)
    currency = models.CharField(max_length=3, default="AFN")
    tax_rate = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("0"))
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    payment_methods = models.JSONField(default=list)
    bank_transfer_instructions = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "store settings"
        verbose_name_plural = "store settings"

    def __str__(self):
        return self.store_name


def current_store_settings():
    saved = StoreSettings.objects.filter(pk=1).first()
    if saved:
        return saved
    return {
        "store_name": settings.OSCAR_SHOP_NAME,
        "tagline": settings.OSCAR_SHOP_TAGLINE,
        "currency": settings.OSCAR_DEFAULT_CURRENCY,
        "tax_rate": str(settings.STORE_TAX_RATE),
        "phone": settings.STORE_PHONE,
        "email": settings.STORE_EMAIL,
        "address": settings.STORE_ADDRESS,
        "payment_methods": ["cod"],
        "bank_transfer_instructions": "",
    }
