from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils.text import slugify
from oscar.core.loading import get_model
from apps.mis.models import Supplier, Expense


class Command(BaseCommand):
    help = "Create safe demo users, permissions and sample store data."

    def handle(self, *args, **options):
        User = get_user_model()
        Product = get_model("catalogue", "Product")
        ProductClass = get_model("catalogue", "ProductClass")
        Category = get_model("catalogue", "Category")
        Partner = get_model("partner", "Partner")
        StockRecord = get_model("partner", "StockRecord")

        permission_codes = [
            "mis.view_possale", "mis.add_possale", "mis.change_possale", "mis.delete_possale", "mis.view_cashiershift", "mis.change_cashiershift",
            "mis.view_stockmovement", "mis.add_stockmovement", "mis.view_purchase", "mis.add_purchase",
            "mis.view_supplier", "mis.add_supplier", "mis.change_supplier", "mis.delete_supplier",
            "mis.view_expense", "mis.add_expense", "mis.change_expense", "mis.delete_expense",
            "mis.view_paymenttransaction", "catalogue.view_product", "catalogue.add_product",
            "catalogue.change_product", "catalogue.delete_product", "auth.view_user", "auth.add_user", "auth.change_user",
        ]

        def perms(codes):
            result = []
            for code in codes:
                app, codename = code.split(".", 1)
                p = Permission.objects.filter(content_type__app_label=app, codename=codename).first()
                if p:
                    result.append(p)
            return result

        owner, _ = User.objects.get_or_create(email="owner@momandsuperstore.com", defaults={"first_name": "Store", "last_name": "Owner"})
        owner.is_staff = True
        owner.is_superuser = True
        owner.is_active = True
        owner.set_password("OwnerDemo123!")
        owner.save()

        admin, _ = User.objects.get_or_create(email="manager@momandsuperstore.com", defaults={"first_name": "Store", "last_name": "Manager"})
        admin.is_staff = True
        admin.is_active = True
        admin.set_password("ManagerDemo123!")
        admin.save()
        admin.user_permissions.set(perms(permission_codes))

        cashier, _ = User.objects.get_or_create(email="cashier@momandsuperstore.com", defaults={"first_name": "Demo", "last_name": "Cashier"})
        cashier.is_staff = True
        cashier.is_active = True
        cashier.set_password("CashierDemo123!")
        cashier.save()
        cashier.user_permissions.set(perms(["catalogue.view_product", "mis.add_possale", "mis.view_possale"]))

        Group.objects.get_or_create(name="Cashier")[0].permissions.set(perms(["mis.view_possale", "mis.add_possale", "mis.view_cashiershift", "mis.change_cashiershift", "catalogue.view_product"]))
        Group.objects.get_or_create(name="Admin")[0].permissions.set(perms(permission_codes))

        supplier, _ = Supplier.objects.get_or_create(name="Demo Wholesale Supplier", defaults={"phone": "0700000000", "address": "Jalalabad"})
        Expense.objects.get_or_create(category="demo-rent", defaults={"amount": Decimal("12000.00"), "description": "Demo shop rent", "created_by": owner})

        pclass, _ = ProductClass.objects.get_or_create(name="General", defaults={"slug": "general"})
        partner, _ = Partner.objects.get_or_create(name="Momand Demo Supplier", defaults={"code": "DEMO"})
        category, _ = Category.objects.get_or_create(name="Demo Grocery", defaults={"slug": "demo-grocery"})

        products = [
            ("Instant Coffee 100 g", "10010001", Decimal("250.00"), 30),
            ("Energy Drink 250 ml", "10010002", Decimal("120.00"), 50),
            ("Bottled Water 1.5 L", "10010003", Decimal("40.00"), 100),
            ("Rice 5 kg", "10010004", Decimal("650.00"), 25),
            ("Biscuits", "10010005", Decimal("80.00"), 40),
        ]
        for title, upc, price, stock in products:
            product, _ = Product.objects.get_or_create(upc=upc, defaults={"title": title, "product_class": pclass, "structure": "standalone", "is_public": True, "slug": slugify(title)})
            product.title = title
            product.product_class = pclass
            product.is_public = True
            product.save()
            product.categories.add(category)
            StockRecord.objects.update_or_create(
                product=product, partner=partner,
                defaults={"price_currency": "AFN", "price_excl_tax": price, "num_in_stock": stock, "num_allocated": 0, "cost_price": price * Decimal("0.75")}
            )

        self.stdout.write(self.style.SUCCESS("Demo data created/updated successfully."))
        self.stdout.write("Owner: owner@momandsuperstore.com / OwnerDemo123!")
        self.stdout.write("Admin: manager@momandsuperstore.com / ManagerDemo123!")
        self.stdout.write("Cashier: cashier@momandsuperstore.com / CashierDemo123!")
