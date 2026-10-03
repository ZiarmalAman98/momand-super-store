from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("mis", "0007_merge_returns_cogs")]
    operations = [
        migrations.CreateModel(name="POSSaleCorrection", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("reason", models.CharField(max_length=240)),
            ("original_total", models.DecimalField(decimal_places=2, max_digits=14, validators=[MinValueValidator(Decimal("0.00"))])),
            ("corrected_total", models.DecimalField(decimal_places=2, max_digits=14, validators=[MinValueValidator(Decimal("0.00"))])),
            ("difference", models.DecimalField(decimal_places=2, max_digits=14)),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("processed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pos_sale_corrections", to=settings.AUTH_USER_MODEL)),
            ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corrections", to="mis.possale")),
        ], options={"ordering":["-created_at","-id"],"indexes":[models.Index(fields=["sale","created_at"],name="mis_corr_sale_created_idx")]}),
        migrations.CreateModel(name="POSSaleCorrectionItem", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("original_quantity", models.PositiveIntegerField()), ("corrected_quantity", models.PositiveIntegerField()), ("quantity_delta", models.IntegerField()),
            ("correction", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="mis.possalecorrection")),
            ("sale_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correction_items", to="mis.possaleitem")),
        ], options={"indexes":[models.Index(fields=["sale_item","correction"],name="mis_pos_corr_sale_i_6a0b9e_idx")]}),
        migrations.AddConstraint(model_name="possalecorrectionitem",constraint=models.CheckConstraint(condition=models.Q(corrected_quantity__gte=1),name="mis_corr_corrected_qty_positive")),
        migrations.AddConstraint(model_name="possalecorrectionitem",constraint=models.CheckConstraint(condition=~models.Q(quantity_delta=0),name="mis_corr_qty_delta_nonzero")),
    ]
