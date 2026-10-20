from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "psae_block_negative_sale")
class TestBlockNegativeSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_salesman = cls.env.ref("sales_team.group_sale_salesman")
        cls.group_bypass = cls.env.ref("psae_block_negative_sale.group_allow_negative_sale")

        cls.user_salesman = cls.env["res.users"].create({
            "name": "Salesman",
            "login": "user_salesman",
            "group_ids": [Command.set([cls.group_salesman.id])],
        })
        cls.user_bypass = cls.env["res.users"].create({
            "name": "Salesman Bypass",
            "login": "user_salesman_bypass",
            "group_ids": [Command.set([cls.group_salesman.id, cls.group_bypass.id])],
        })

        cls.stock_location = cls.env.ref("stock.stock_location_stock")

        cls.product = cls.env["product.product"].create({
            "name": "Test Storable Product",
            "type": "consu",
            "is_storable": True,
            "list_price": 100.0,
        })
        cls.product_lot = cls.env["product.product"].create({
            "name": "Test Lot Product",
            "type": "consu",
            "is_storable": True,
            "tracking": "lot",
        })
        cls.product_serial = cls.env["product.product"].create({
            "name": "Test Serial Product",
            "type": "consu",
            "is_storable": True,
            "tracking": "serial",
        })

        for product in (cls.product, cls.product_lot, cls.product_serial):
            cls.env["stock.quant"].search([("product_id", "=", product.id)]).unlink()

    def _make_order(self, *line_specs, user=None):
        """Create a sale order. Each spec is (qty,) using self.product, or (product, qty)."""
        lines = [
            Command.create({"product_id": (self.product if len(s) == 1 else s[0]).id, "product_uom_qty": s[-1]})
            for s in line_specs
        ]
        return (
            self
            .env["sale.order"]
            .with_user(user or self.user_salesman)
            .create({
                "partner_id": (user or self.user_salesman).partner_id.id,
                "order_line": lines,
            })
        )

    def _set_stock(self, qty, product=None, lot=None):
        self.env["stock.quant"]._update_available_quantity(
            product or self.product, self.stock_location, qty, lot_id=lot
        )

    def _make_lot(self, name, product):
        return self.env["stock.lot"].create({"name": name, "product_id": product.id})

    # --- Hard block on confirm ---

    def test_01_insufficient_stock_blocks_confirm(self):
        """0 stock, 5 demanded → UserError on confirm."""
        so = self._make_order((5.0,))
        with self.assertRaises(UserError):
            so.action_confirm()

    def test_02_sufficient_stock_confirms_normally(self):
        """10 on hand, 5 demanded → confirm succeeds."""
        self._set_stock(10.0)
        so = self._make_order((5.0,))
        so.action_confirm()
        self.assertEqual(so.state, "sale")

    def test_03_exact_stock_confirms_normally(self):
        """Stock exactly equals demand → not blocked (float_compare < 0 is False at equality)."""
        self._set_stock(5.0)
        so = self._make_order((5.0,))
        so.action_confirm()
        self.assertEqual(so.state, "sale")

    def test_04_bypass_group_overrides_block(self):
        """User with group_allow_negative_sale can confirm despite 0 stock."""
        so = self._make_order((5.0,), user=self.user_bypass)
        so.action_confirm()
        self.assertEqual(so.state, "sale")

    # --- Adding lines to a confirmed SO ---

    def test_05_adding_line_to_confirmed_so_blocks(self):
        """Confirm with stock, then add a line that exceeds remaining stock → blocked."""
        self._set_stock(10.0)
        so = self._make_order((5.0,))
        so.action_confirm()
        self.assertEqual(so.state, "sale")

        # Drain the stock so the new line has no coverage
        self._set_stock(-10.0)

        with self.assertRaises(UserError):
            so.with_user(self.user_salesman).write({
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 3.0})]
            })

    def test_06_bypass_adding_line_to_confirmed_so(self):
        """Bypass user can add insufficient-stock line to a confirmed SO."""
        self._set_stock(10.0)
        so = self._make_order((5.0,), user=self.user_bypass)
        so.action_confirm()

        self._set_stock(-10.0)

        so.with_user(self.user_bypass).write({
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 3.0})]
        })
        self.assertEqual(so.state, "sale")

    # --- Lot / serial tracking ---

    def test_07_lot_tracked_insufficient_blocks(self):
        """4 total across lots, 6 demanded → blocked."""
        lot_1 = self._make_lot("LOT001", self.product_lot)
        lot_2 = self._make_lot("LOT002", self.product_lot)
        self._set_stock(2.0, product=self.product_lot, lot=lot_1)
        self._set_stock(2.0, product=self.product_lot, lot=lot_2)
        so = self._make_order((self.product_lot, 6.0))
        with self.assertRaises(UserError):
            so.action_confirm()

    def test_08_lot_tracked_sufficient_confirms(self):
        """6 total across lots, 5 demanded → confirm succeeds."""
        lot_1 = self._make_lot("LOT003", self.product_lot)
        lot_2 = self._make_lot("LOT004", self.product_lot)
        self._set_stock(3.0, product=self.product_lot, lot=lot_1)
        self._set_stock(3.0, product=self.product_lot, lot=lot_2)
        so = self._make_order((self.product_lot, 5.0))
        so.action_confirm()
        self.assertEqual(so.state, "sale")

    def test_09_serial_tracked_insufficient_blocks(self):
        """1 serial on hand, 3 demanded → blocked."""
        sn_1 = self._make_lot("SN001", self.product_serial)
        self._set_stock(1.0, product=self.product_serial, lot=sn_1)
        so = self._make_order((self.product_serial, 3.0))
        with self.assertRaises(UserError):
            so.action_confirm()

    def test_10_two_lines_one_short_blocks(self):
        """Line 1 sufficient, Line 2 short → whole confirm is blocked."""
        self._set_stock(10.0)
        so = self._make_order((self.product, 5.0), (self.product_lot, 3.0))
        with self.assertRaises(UserError):
            so.action_confirm()

    def test_11_service_product_not_blocked(self):
        """Service product: display_qty_widget=False → never blocked regardless of stock."""
        product_service = self.env["product.product"].create({
            "name": "Service Product",
            "type": "service",
        })
        so = self._make_order((product_service, 100.0))
        so.action_confirm()
        self.assertEqual(so.state, "sale")
