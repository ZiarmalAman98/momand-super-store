from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from oscar.core.loading import get_model

from apps.mis.models import Supplier

Category = get_model("catalogue", "Category")
Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
Partner = get_model("partner", "Partner")
StockRecord = get_model("partner", "StockRecord")


CATALOGUE = [
    ("food-grocery", "Food & Grocery"), ("beverages", "Beverages"),
    ("energy-drinks", "Energy Drinks"), ("snacks", "Snacks"),
    ("dairy", "Dairy"), ("bakery", "Bakery"), ("fruits", "Fruits"),
    ("vegetables", "Vegetables"), ("frozen-foods", "Frozen Foods"),
    ("household", "Household"), ("cleaning-products", "Cleaning Products"),
    ("personal-care", "Personal Care"), ("cosmetics", "Cosmetics"),
    ("baby-products", "Baby Products"), ("stationery", "Stationery"),
    ("electronics", "Electronics"), ("other", "Other"),
]

PRODUCTS = [
    ("100000000001", "Basmati Rice 5 kg", "food-grocery", "MOM-RICE-5KG", "450.00", 45, 8),
    ("100000000002", "Sunflower Cooking Oil 1 L", "food-grocery", "MOM-OIL-1L", "120.00", 60, 10),
    ("100000000003", "Drinking Water 1.5 L", "beverages", "MOM-WATER-15", "25.00", 120, 20),
    ("100000000004", "Whole Milk 1 L", "dairy", "MOM-MILK-1L", "65.00", 38, 8),
    ("100000000005", "Fresh Bread Loaf", "bakery", "MOM-BREAD-01", "35.00", 30, 6),
    ("100000000006", "Mixed Biscuits 300 g", "snacks", "MOM-BISCUIT-3", "55.00", 50, 10),
    ("100000000007", "Laundry Detergent 1 kg", "cleaning-products", "MOM-DET-1KG", "95.00", 32, 7),
    ("100000000008", "Bath Soap 100 g", "personal-care", "MOM-SOAP-100", "28.00", 75, 12),
    ("100000000009", "Baby Diapers Pack", "baby-products", "MOM-DIAPER-01", "390.00", 18, 5),
    ("100000000010", "Exercise Notebook", "stationery", "MOM-NOTE-A5", "40.00", 25, 5),
    ("100000000011", "Orange Juice 1 L", "beverages", "MOM-JUICE-1L", "85.00", 42, 8),
    ("100000000012", "Green Tea 100 g", "food-grocery", "MOM-TEA-100", "110.00", 22, 5),
]


class Command(BaseCommand):
    help = "Add idempotent Momand supermarket categories, sample products, a store stock source, and supplier."

    def handle(self, *args, **options):
        categories = {}
        for slug, name in CATALOGUE:
            category = Category.objects.filter(slug=slug).first()
            if category is None:
                category = Category.add_root(name=name, slug=slug, description=f"Shop {name.lower()} at Momand Super Store.")
            categories[slug] = category

        product_class, _ = ProductClass.objects.get_or_create(
            name="Supermarket goods", defaults={"requires_shipping": True, "track_stock": True}
        )
        partner, _ = Partner.objects.get_or_create(name="Momand Main Store")
        created_products = 0
        for barcode, title, category_slug, sku, price, quantity, minimum in PRODUCTS:
            product = Product.objects.filter(upc=barcode).first()
            if product is None:
                product = Product.objects.create(
                    structure=Product.STANDALONE, is_public=True, upc=barcode,
                    title=title, description=f"{title} available from Momand Super Store.",
                    product_class=product_class,
                )
                product.categories.add(categories[category_slug])
                created_products += 1
            else:
                product.categories.add(categories[category_slug])
            record, created = StockRecord.objects.get_or_create(
                product=product, partner=partner,
                defaults={
                    "partner_sku": sku, "price_currency": settings.OSCAR_DEFAULT_CURRENCY,
                    "price": Decimal(price), "num_in_stock": quantity,
                    "low_stock_threshold": minimum,
                },
            )
            if created:
                # Initial catalogue seed is itself represented in the stock ledger.
                from apps.mis.models import StockMovement
                StockMovement.objects.create(
                    stockrecord=record, movement_type=StockMovement.TYPE_OPENING,
                    quantity_delta=quantity, quantity_before=0, quantity_after=quantity,
                    reference="SEED-DATA", note="Initial development seed stock",
                )
        supplier, supplier_created = Supplier.objects.get_or_create(
            name="Momand Wholesale Supply",
            defaults={"contact_name": "Store purchasing desk", "phone": settings.STORE_PHONE},
        )
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CATALOGUE)} categories, {created_products} new products, "
            f"store source {partner.name}, supplier {'created' if supplier_created else 'present'}: {supplier.name}."
        ))
