from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mis", "0004_cashier_shift"),
    ]

    operations = [
        migrations.AlterField(
            model_name="possale",
            name="payment_method",
            field=models.CharField(choices=[("cash", "Cash"), ("card", "Card"), ("bank_transfer", "Bank transfer"), ("split", "Split payment")], max_length=20),
        ),
    ]
