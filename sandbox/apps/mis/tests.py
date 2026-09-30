from decimal import Decimal\nfrom datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from oscar.test.factories import ProductFactory

from .models import CashierShift, PaymentTransaction, POSSale, Purchase, StockMovement, Supplier
from .services import adjust_stock, close_cashier_shift, create_pos_sale, open_cashier_shift, process_pos_return, receive_purchase\nfrom .accounting import financial_summary


class InventoryTransactionTests(TestCase):
    def setUp(self):
        self.cashier = get_user_model().objects.create_user(username="cashier-test", password="SecurePass!12345")
        self.product = ProductFactory(stockrecords__price=Decimal("12.50"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=8, stockrecords__cost_price=Decimal("8.00"))
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
        self.assertEqual(sale.items.first().unit_cost, Decimal("8.00"))
        self.assertEqual(sale.items.first().cost_total, Decimal("16.00"))
        self.assertEqual(movement.quantity_delta, -2)
        self.assertEqual(movement.quantity_before, 8)
        self.assertEqual(movement.quantity_after, 6)

    def test_split_payment_creates_multiple_payment_transactions(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"product_id": self.product.pk, "quantity": 2}],
            payment_lines=[
                {"method": POSSale.PAYMENT_CASH, "amount": "10.00", "tendered": "20.00"},
                {"method": POSSale.PAYMENT_CARD, "amount": "15.00"},
            ],
        )
        payments = list(PaymentTransaction.objects.filter(sale=sale).order_by("transaction_ref"))
        self.assertEqual(sale.payment_method, POSSale.PAYMENT_SPLIT)
        self.assertEqual(sale.amount_tendered, Decimal("35.00"))
        self.assertEqual(sale.change_due, Decimal("10.00"))
        self.assertEqual([p.amount for p in payments], [Decimal("10.00"), Decimal("15.00")])
        self.assertEqual([p.method for p in payments], [POSSale.PAYMENT_CASH, POSSale.PAYMENT_CARD])

    def test_split_payment_must_equal_sale_total(self):
        with self.assertRaises(ValidationError):
            create_pos_sale(
                cashier=self.cashier,
                items=[{"product_id": self.product.pk, "quantity": 2}],
                payment_lines=[{"method": POSSale.PAYMENT_CASH, "amount": "10.00", "tendered": "10.00"}],
            )
        self.assertEqual(POSSale.objects.count(), 0)

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

    def test_sale_requires_inventory_cost(self):
        self.record.cost_price = None
        self.record.save(update_fields=["cost_price"])
        with self.assertRaises(ValidationError):
            create_pos_sale(
                cashier=self.cashier,
                items=[{"product_id": self.product.pk, "quantity": 1}],
                payment_method=POSSale.PAYMENT_CASH,
                amount_tendered="13.75",
            )
        self.assertEqual(POSSale.objects.count(), 0)

    def test_return_snapshots_cogs_and_restock_reverses_it(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"product_id": self.product.pk, "quantity": 2}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="30.00",
        )
        returned = process_pos_return(
            invoice_number=sale.invoice_number,
            processed_by=self.cashier,
            items=[{"sale_item_id": sale.items.first().pk, "quantity": 1}],
            refund_method=POSSale.PAYMENT_CASH,
            reason="COGS return",
            restocked=True,
        )
        item = returned.items.get()
        self.assertEqual(item.unit_cost, Decimal("8.00"))
        self.assertEqual(item.cost_total, Decimal("8.00"))

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
        self.assertEqual(self.record.cost_price, Decimal("8.10"))
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

    def test_cashier_shift_open_and_close_calculates_difference(self):
        shift = open_cashier_shift(cashier=self.cashier, opening_cash="100.00")
        self.assertEqual(shift.status, CashierShift.STATUS_OPEN)
        self.assertEqual(shift.opening_cash, Decimal("100.00"))

        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"product_id": self.product.pk, "quantity": 2}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="30.00",
        )
        closed = close_cashier_shift(shift_id=shift.pk, closing_cash="124.00", note="End of day")
        self.assertEqual(closed.expected_cash, sale.total + Decimal("100.00"))
        self.assertEqual(closed.closing_cash, Decimal("124.00"))
        self.assertEqual(closed.cash_difference, Decimal("-1.00"))
        self.assertEqual(closed.status, CashierShift.STATUS_CLOSED)
        self.assertIsNotNone(closed.closed_at)

    def test_cashier_cannot_open_two_shifts(self):
        open_cashier_shift(cashier=self.cashier, opening_cash="50.00")
        with self.assertRaises(ValidationError):
            open_cashier_shift(cashier=self.cashier, opening_cash="75.00")

    def test_cash_refund_is_subtracted_from_shift_expected_cash(self):
        shift = open_cashier_shift(cashier=self.cashier, opening_cash="100.00")
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
            reason="Customer return",
            restocked=True,
        )
        closed = close_cashier_shift(shift_id=shift.pk, closing_cash="111.25")
        self.assertEqual(returned.refund_total, Decimal("12.50"))
        self.assertEqual(closed.expected_cash, Decimal("112.50"))

\n\nclass FinancialReportTests(TestCase):\n    def setUp(self):\n        self.cashier = get_user_model().objects.create_user(username="report-cashier", password="SecurePass!12345")\n        self.product = ProductFactory(stockrecords__price=Decimal("10.00"), stockrecords__price_currency="AFN", stockrecords__num_in_stock=20, stockrecords__cost_price=Decimal("6.00"))\n        self.supplier = Supplier.objects.create(name="Report Supplier")\n\n    def test_financial_summary_includes_sales_refunds_purchases_and_expenses(self):\n        sale = create_pos_sale(\n            cashier=self.cashier,\n            items=[{"product_id": self.product.pk, "quantity": 2}],\n            payment_method=POSSale.PAYMENT_CASH,\n            amount_tendered="20.00",\n        )\n        line = sale.items.get()\n        process_pos_return(\n            invoice_number=sale.invoice_number,\n            processed_by=self.cashier,\n            items=[{"sale_item_id": line.pk, "quantity": 1}],\n            refund_method=POSSale.PAYMENT_CASH,\n            reason="Report test",\n            restocked=True,\n        )\n        receive_purchase(\n            supplier=self.supplier, reference="REPORT-INV-001", purchased_at=timezone.localdate(),\n            items=[{"product_id": self.product.pk, "quantity": 3, "unit_cost": "6.00"}],\n            created_by=self.cashier,\n        )\n        Expense.objects.create(category=Expense.CATEGORY_OTHER, description="Report expense", amount="5.00", created_by=self.cashier)\n        report = financial_summary(start_date=timezone.localdate(), end_date=timezone.localdate())\n        self.assertEqual(report["pos_sales"]["gross"], "20.00")\n        self.assertEqual(report["pos_sales"]["refunds"], "10.00")\n        self.assertEqual(report["pos_sales"]["net"], "10.00")\n        self.assertEqual(report["purchases"]["total"], "18.00")\n        self.assertEqual(report["expenses"]["total"], "5.00")\n        self.assertEqual(report["cash"]["net"], "10.00")\n        self.assertEqual(report["accounting_status"], "cogs_modeled")\n\n    def test_financial_summary_calculates_cogs_and_profit(self):
        sale = create_pos_sale(
            cashier=self.cashier,
            items=[{"product_id": self.product.pk, "quantity": 2}],
            payment_method=POSSale.PAYMENT_CASH,
            amount_tendered="20.00",
        )
        process_pos_return(
            invoice_number=sale.invoice_number,
            processed_by=self.cashier,
            items=[{"sale_item_id": sale.items.first().pk, "quantity": 1}],
            refund_method=POSSale.PAYMENT_CASH,
            reason="Profit test",
            restocked=True,
        )
        report = financial_summary(
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        self.assertEqual(report["cogs"]["pos"], "12.00")
        self.assertEqual(report["cogs"]["returned_restocked"], "6.00")
        self.assertEqual(report["cogs"]["net"], "6.00")
        self.assertEqual(report["profit"]["gross"], "4.00")
        self.assertEqual(report["profit"]["net"], "4.00")
        self.assertEqual(report["accounting_status"], "cogs_modeled")

    def test_financial_summary_rejects_reversed_date_range(self):\n        today = timezone.localdate()\n        with self.assertRaises(ValueError):\n            financial_summary(start_date=today, end_date=today - timedelta(days=1))\n