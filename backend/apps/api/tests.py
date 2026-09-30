from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase
from decimal import Decimal
from oscar.test.factories import ProductFactory
from apps.mis.models import StockMovement, Supplier
from apps.mis.tests import InventoryTransactionTests


class PublicApiTests(APITestCase):
    def test_products_and_categories_are_public(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/categories/").status_code, 200)

    def test_customer_registration_and_email_login(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        payload = {
            "email": "buyer@example.test",
            "first_name": "Store",
            "last_name": "Customer",
            "password": "SecureCustomerPassword!2026",
            "password_confirm": "SecureCustomerPassword!2026",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        login = self.client.post(
            "/api/v1/auth/token/",
            {"email": payload["email"], "password": payload["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)
        self.assertTrue(login.cookies.get("momand_refresh"))
        self.assertTrue(get_user_model().objects.filter(email=payload["email"]).exists())

    def test_orders_require_authentication(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 401)

    def test_pos_search_requires_cashier_group_permission(self):
        user = get_user_model().objects.create_user(username="pos-permission-test", password="SecurePass!12345", is_staff=True)
        product = ProductFactory(stockrecords__price=Decimal("2.00"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=2)
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get("/api/v1/pos/products/", {"search": product.upc}).status_code, 403)
        permission = Permission.objects.get(content_type__app_label="catalogue", codename="view_product")
        cashier = Group.objects.create(name="Temporary cashier")
        cashier.permissions.add(permission)
        user.groups.add(cashier)
        user = get_user_model().objects.get(pk=user.pk)
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/pos/products/", {"search": product.upc})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], product.pk)

    def test_pos_api_sale_decrements_stock_and_returns_invoice(self):
        user = get_user_model().objects.create_user(username="pos-sale-test", password="SecurePass!12345", is_staff=True)
        product = ProductFactory(stockrecords__price=Decimal("3.50"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=4)
        permission = Permission.objects.get(content_type__app_label="mis", codename="add_possale")
        cashier = Group.objects.create(name="Temporary cashier sale")
        cashier.permissions.add(permission)
        user.groups.add(cashier)
        self.client.force_authenticate(user=user)
        response = self.client.post("/api/v1/pos/sales/create/", {
            "items": [{"product_id": product.pk, "quantity": 2}],
            "payment_method": "cash",
            "amount_tendered": "10.00",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["change_due"], "3.00")
        self.assertEqual(product.stockrecords.get().num_in_stock, 2)

    def test_purchase_receive_increases_stock_with_permission_and_ledger(self):
        user = get_user_model().objects.create_user(username="purchase-test", password="SecurePass!12345", is_staff=True)
        product = ProductFactory(stockrecords__price=Decimal("3.50"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=4)
        supplier = Supplier.objects.create(name="Purchase API Supplier")
        group = Group.objects.create(name="Temporary purchase manager")
        group.permissions.add(Permission.objects.get(content_type__app_label="mis", codename="add_purchase"))
        user.groups.add(group)
        self.client.force_authenticate(user=user)
        response = self.client.post("/api/v1/purchases/receive/", {
            "supplier_id": supplier.pk,
            "reference": "SUP-INV-API-1",
            "items": [{"product_id": product.pk, "quantity": 6, "unit_cost": "2.25"}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        record = product.stockrecords.get()
        record.refresh_from_db()
        self.assertEqual(record.num_in_stock, 10)
        self.assertEqual(response.data["total_cost"], "13.50")
        self.assertEqual(StockMovement.objects.get(reference="SUP-INV-API-1").quantity_delta, 6)

    def test_dashboard_summary_requires_sales_permission(self):
        user = get_user_model().objects.create_user(username="dashboard-test", password="SecurePass!12345", is_staff=True)
        permission = Permission.objects.get(content_type__app_label="mis", codename="view_possale")
        group = Group.objects.create(name="Temporary dashboard manager")
        group.permissions.add(permission)
        user.groups.add(group)
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/reports/dashboard/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("today_sales", response.data)
        self.assertIn("daily_sales", response.data)

    def test_partial_pos_return_restores_stock_and_reduces_returnable_quantity(self):
        user = get_user_model().objects.create_user(username="pos-return-test", password="SecurePass!12345", is_staff=True)
        product = ProductFactory(stockrecords__price=Decimal("3.50"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=4)
        group = Group.objects.create(name="Temporary return manager")
        group.permissions.add(
            Permission.objects.get(content_type__app_label="mis", codename="add_possale"),
            Permission.objects.get(content_type__app_label="mis", codename="view_possale"),
            Permission.objects.get(content_type__app_label="mis", codename="add_possalereturn"),
        )
        user.groups.add(group)
        self.client.force_authenticate(user=user)
        sale_response = self.client.post("/api/v1/pos/sales/create/", {
            "items": [{"product_id": product.pk, "quantity": 2}],
            "payment_method": "cash", "amount_tendered": "10.00",
        }, format="json")
        self.assertEqual(sale_response.status_code, 201, sale_response.data)
        sale = sale_response.data
        return_response = self.client.post(f"/api/v1/pos/sales/{sale['invoice_number']}/returns/", {
            "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": 1}],
            "refund_method": "cash", "reason": "Customer return", "restocked": True,
        }, format="json")
        self.assertEqual(return_response.status_code, 201, return_response.data)
        self.assertEqual(return_response.data["refund_total"], "3.50")
        product.stockrecords.get().refresh_from_db()
        self.assertEqual(product.stockrecords.get().num_in_stock, 3)
        detail = self.client.get(f"/api/v1/pos/sales/{sale['invoice_number']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["items"][0]["returnable_quantity"], 1)
