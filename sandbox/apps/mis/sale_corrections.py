from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class POSSaleCorrection(models.Model):
    sale = models.ForeignKey(
        "apps.mis.POSSale", on_delete=models.PROTECT, related_name="corrections"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pos_sale_corrections"
    )
    reason = models.CharField(max_length=240)
    original_total = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    corrected_total = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    difference = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["sale", "created_at"], name="mis_pos_sale_sale_id_7f9e5b_idx")]


class POSSaleCorrectionItem(models.Model):
    correction = models.ForeignKey(
        POSSaleCorrection, on_delete=models.PROTECT, related_name="items"
    )
    sale_item = models.ForeignKey(
        "apps.mis.POSSaleItem", on_delete=models.PROTECT, related_name="correction_items"
    )
    original_quantity = models.PositiveIntegerField()
    corrected_quantity = models.PositiveIntegerField()
    quantity_delta = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(corrected_quantity__gte=1), name="mis_corr_corrected_qty_positive"),
            models.CheckConstraint(condition=~models.Q(quantity_delta=0), name="mis_corr_qty_delta_nonzero"),
        ]
        indexes = [models.Index(fields=["sale_item", "correction"], name="mis_pos_corr_sale_i_6a0b9e_idx")]
