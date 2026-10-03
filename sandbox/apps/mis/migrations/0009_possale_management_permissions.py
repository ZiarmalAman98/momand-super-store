from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("mis", "0008_sale_correction")]

    operations = [
        migrations.AlterModelOptions(
            name="possale",
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("view_possale_all", "Can view all POS sales"),
                    ("view_dashboard", "Can view the business dashboard"),
                    ("view_financialreport", "Can view financial reports"),
                ],
            },
        ),
    ]
