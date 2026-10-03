from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class POSSaleCorrection(models.Model):
    sale = models.ForeignKey(
        "mis.POSSale",
        on_delete=models.PROTECT,
        related_name="corrections",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pos_sale_corrections",
    )
    reason = models.CharField(max_length=240)
    original_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    corrected_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["sale", "created_at"],
                name="mis_corr_sale_created_idx",
            ),
        ]

    def __str__(self):
        return f"Correction #{self.pk} - {self.sale}"


class POSSaleCorrectionItem(models.Model):
    correction = models.ForeignKey(
        POSSaleCorrection,
        on_delete=models.PROTECT,
        related_name="items",
    )
    sale_item = models.ForeignKey(
        "mis.POSSaleItem",
        on_delete=models.PROTECT,
        related_name="correction_items",
    )
    original_quantity = models.PositiveIntegerField()
    corrected_quantity = models.PositiveIntegerField()
    quantity_delta = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(corrected_quantity__gte=1),
                name="mis_corr_corrected_qty_positive",
            ),
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="mis_corr_qty_delta_nonzero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["sale_item", "correction"],
                name="mis_pos_corr_sale_i_6a0b9e_idx",
            ),
        ]

    def __str__(self):
        return f"Correction item #{self.pk}"


class POSSaleCorrectionRequest(models.Model):
    sale = models.ForeignKey("mis.POSSale", on_delete=models.PROTECT, related_name="correction_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pos_correction_requests")
    reason = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_pos_correction_requests")
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["is_resolved", "-created_at", "-id"]
        indexes = [models.Index(fields=["is_resolved", "created_at"], name="mis_corr_req_open_created_idx")]

    def mark_resolved(self, user):
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])

    def __str__(self):
        return f"Correction request for {self.sale}"
