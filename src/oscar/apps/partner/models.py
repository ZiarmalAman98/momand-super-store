from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from oscar.apps.address.abstract_models import AbstractPartnerAddress
from oscar.apps.partner.abstract_models import (
    AbstractPartner,
    AbstractStockAlert,
    AbstractStockRecord,
)
from oscar.core.loading import is_model_registered

__all__ = []


if not is_model_registered("partner", "Partner"):

    class Partner(AbstractPartner):
        pass

    __all__.append("Partner")


if not is_model_registered("partner", "PartnerAddress"):

    class PartnerAddress(AbstractPartnerAddress):
        pass

    __all__.append("PartnerAddress")


if not is_model_registered("partner", "StockRecord"):

    class StockRecord(AbstractStockRecord):
        price = models.DecimalField(
            "Price",
            decimal_places=2,
            max_digits=12,
            blank=True,
            null=True,
            validators=[MinValueValidator(0)],
        )
        num_allocated = models.IntegerField(
            "Number allocated",
            blank=True,
            null=True,
            validators=[MinValueValidator(0)],
        )

        class Meta:
            constraints = [
                models.CheckConstraint(
                    condition=Q(num_allocated__gte=0) | Q(num_allocated__isnull=True),
                    name="oscar_stock_allocated_nonnegative",
                ),
                models.CheckConstraint(
                    condition=Q(price__gte=0) | Q(price__isnull=True),
                    name="oscar_stock_price_nonnegative",
                ),
            ]
            indexes = [
                models.Index(fields=["product", "partner"]),
                models.Index(fields=["partner", "date_updated"]),
            ]

    __all__.append("StockRecord")


if not is_model_registered("partner", "StockAlert"):

    class StockAlert(AbstractStockAlert):
        pass

    __all__.append("StockAlert")
