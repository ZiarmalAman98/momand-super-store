from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from oscar.test.factories import ProductFactory

from .models import PaymentTransaction, POSSale, Purchase, StockMovement, Supplier
from .services import adjust_stock, create_pos_sale, process_pos_return, receive_purchase


class InventoryTransactionTests(TestCase):
    def setUp(self):
        self.cashier = get_user_model().objects.create_user(username="cashier-test", password="SecurePass!12345")
        self.product = ProductFactory(stockrecords__price=Decimal("12.50"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=8)
        self.record = self.product.stockrecords.get()

    def test_pos_sale_records_payment_and_stock_movement(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"barcode": self.product.upc, "quantity": 2}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="30.00",
        )
        self.record.refresh_from_db()
        movement = StockMovement.objects.get(reference=sale.invoice_number)
        payment = PaymentTransaction.objects.get(sale=sale)
        self.assertEqual(payment.status, PaymentTransaction.STATUS_PAID)
        self.assertEqual(payment.amount, sale.total)
        self.assertEqual(payment.method, POSSale.PAYMENT_CASH)
        self.assertEqual(payment.gateway, "pos")
        self.assertEqual(sale.total, Decimal("25.00"))
        self.assertEqual(sale.change_due, Decimal("5.00"))
        self.assertEqual(self.record.num_in_stock, 6)
        self.assertEqual(movement.quantity_delta, -2)
        self.assertEqual(movement.quantity_before, 8)
        self.assertEqual(movement.quantity_after, 6)

    def test_duplicate_scanner_lines_are_aggregated_before_stock_deduction(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"barcode": self.product.upc, "quantity": 2}, {"product_id": self.product.pk, "quantity": 3}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="70.00",
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.num_in_stock, 3)
        self.assertEqual(sale.items.count(), 1)
        self.assertEqual(sale.items.first().quantity, 5)

    def test_insufficient_pos_stock_leaves_sale_and_stock_unchanged(self):
        with self.assertRaises(ValidationError):
            create_pos_sale(
                cashier=self.cashier,
                items=[{"product_id": self.product.pk, "quantity": 9}],
                payment_method=POSSale.PAYMENT_CASH,
                amount_tendered="200.00",
            )
        self.record.refresh_from_db()
        self.assertEqual(self.record.num_in_stock, 8)
        self.assertEqual(POSSale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_receiving_purchase_adds_stock_and_audits_change(self):
        supplier = Supplier.objects.create(name="Inventory Test Supplier")
        purchase = receive_purchase(
            supplier=supplier,
            reference="INV-TEST-001",
            purchased_at=Purchase._meta.get_field("purchased_at").get_default(),
            items=[{"product_id": self.product.pk, "quantity": 5, "unit_cost": "8.25"}],
            created_by=self.cashier,
        )
        self.record.refresh_from_db()
        movement = StockMovement.objects.get(reference=purchase.reference)
        self.assertEqual(purchase.total_cost, Decimal("41.25"))
        self.assertEqual(purchase.status, Purchase.STATUS_RECEIVED)
        self.assertEqual(self.record.num_in_stock, 13)
        self.assertEqual(movement.quantity_delta, 5)

    def test_pos_sale_cannot_consume_reserved_stock(self):
        self.record.num_allocated = 7
        self.record.save(update_fields=["num_allocated"])

        with self.assertRaises(ValidationError):
            create_pos_sale(
                cashier=self.cashier,
                items=[{"product_id": self.product.pk, "quantity": 2}],
                payment_method=POSSale.PAYMENT_CASH,
                amount_tendered="30.00",
            )

        self.record.refresh_from_db()
        self.assertEqual(self.record.num_in_stock, 8)
        self.assertEqual(self.record.num_allocated, 7)
        self.assertEqual(POSSale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_adjustment_cannot_reduce_reserved_stock(self):
        self.record.num_allocated = 3
        self.record.save(update_fields=["num_allocated"])
        with self.assertRaises(ValidationError):
            adjust_stock(
                stockrecord_id=self.record.pk,
                quantity_delta=-6,
                reason=StockMovement.TYPE_DAMAGE,
                created_by=self.cashier,
            )
        self.record.refresh_from_db()
        self.assertEqual(self.record.num_in_stock, 8)
        self.assertEqual(StockMovement.objects.count(), 0)

    @override_settings(STORE_TAX_RATE="0.10")
    def test_partial_return_refunds_recorded_tax_and_restocks_when_selected(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"product_id": self.product.pk, "quantity": 2}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="30.00",
        )
        line = sale.items.get()
        returned = process_pos_return(
            invoice_number=sale.invoice_number,
            processed_by=self.cashier,
            items=[{"sale_item_id": line.pk, "quantity": 1}],
            refund_method=POSSale.PAYMENT_CASH,
            reason="Package damaged",
            restocked=True,
        )
        self.record.refresh_from_db()
        self.assertEqual(sale.tax, Decimal("2.50"))
        self.assertEqual(returned.refund_total, Decimal("13.75"))
        self.assertEqual(self.record.num_in_stock, 7)
        self.assertEqual(StockMovement.objects.filter(reference=returned.invoice_number).get().quantity_delta, 1)
        with self.assertRaises(ValidationError):
            process_pos_return(
                invoice_number=sale.invoice_number, processed_by=self.cashier,
                items=[{"sale_item_id": line.pk, "quantity": 2}],
                refund_method=POSSale.PAYMENT_CASH, reason="Duplicate return", restocked=True,
            )
