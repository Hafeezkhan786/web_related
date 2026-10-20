import logging

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "psae_block_negative_pos")
class TestPOSBlockNegSale(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref("point_of_sale.group_pos_manager")

        cls.employee_A, cls.employee_B = (
            cls
            .env["hr.employee"]
            .sudo()
            .create([
                {
                    "name": "Employee A",
                    "user_id": False,
                    "work_email": "employee_A@example.com",
                },
                {
                    "name": "Employee B",
                    "user_id": False,
                    "work_email": "employee_B@example.com",
                },
            ])
        )
        (cls.whiteboard_pen + cls.wall_shelf).write({"is_storable": True})

    # Close any unclosed POS sessions after each test.
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        open_sessions = cls.env["pos.session"].search(fields.Domain("state", "!=", "open"))
        for session in open_sessions:
            session.post_closing_cash_details(0)
            session.close_session_from_ui()

    def test_user_disabled_neg_qty_sell_tour(self):
        """User has no allow-negative permission. Negative qty sale is blocked."""
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": False})
        self.assertFalse(self.wall_shelf.is_negative_pos_allowed, "Products should be set to disallow negative stock")
        self.assertFalse(
            self.whiteboard_pen.is_negative_pos_allowed, "Products should be set to disallow negative stock"
        )
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(
            url,
            "disabled_neg_qty_tour",
            login="pos_user",
        )

    def test_pos_emp_field_set_tour(self):
        """Employee B set as advanced — negative sale allowed. Employee B removed — negative sale blocked. Config changes take effect."""
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": False})
        self.assertFalse(
            self.whiteboard_pen.is_negative_pos_allowed, "Products should be set to disallow negative stock"
        )
        self.assertFalse(self.wall_shelf.is_negative_pos_allowed, "Products should be set to disallow negative stock")
        self.main_pos_config.write({"module_pos_hr": True})
        self.main_pos_config.write({"advanced_employee_ids": [Command.set(self.employee_B.ids)]})
        self.env.flush_all()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "pos_employee_successful_payment_confirm_negative_warning", login="pos_admin")

        # Close the session so the next open_ui() starts fresh
        session = self.main_pos_config.current_session_id
        session.post_closing_cash_details(0)
        session.close_session_from_ui()

        self.main_pos_config.write({
            "advanced_employee_ids": [Command.set(self.employee_A.ids)]
        })  # setting employee A, removing employee B, tour runs on B but we need at least one
        self.main_pos_config.write({
            "basic_employee_ids": [Command.set(self.employee_B.ids)]
        })  # setting employee A, removing employee B, tour runs on B but we need at least one
        self.env.flush_all()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(
            url,
            "pos_employee_unsuccessful_payment",
            login="pos_admin",
        )

    def test_pos_product_allowed_neg_tour(self):
        """Products have allow_negative=True. Negative qty sale is allowed per-product override."""
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": True})
        self.assertTrue(self.whiteboard_pen.is_negative_pos_allowed, "Products should be set to allow negative stock")
        self.assertTrue(self.wall_shelf.is_negative_pos_allowed, "Products should be set to allow negative stock")
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "enabled_neg_qty_tour", login="pos_user")

    def test_pos_product_sell_tour_01(self):
        """Stock in a separate warehouse. Block source = operation type → allowed. Block source = warehouse → blocked."""
        warehouse = self.env["stock.warehouse"].create({"name": "WH-Demo", "code": "demowh"})
        self.main_pos_config.write({"picking_type_id": warehouse.pos_type_id.id})
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": False})
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": warehouse.pos_type_id.default_location_src_id.id,
            },
            {
                "product_id": self.wall_shelf.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": warehouse.pos_type_id.default_location_src_id.id,
            },
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "enabled_neg_qty_tour", login="pos_user")

        self.main_pos_config.write({"negative_qty_block_source": "warehouse"})
        self.main_pos_config.open_ui()
        self.start_tour(url, "unsuccessful_payment_tour", login="pos_user")

    def test_pos_product_sell_tour_02(self):
        """Block source = warehouse. Stock is in the POS warehouse. Sale is allowed."""
        self.main_pos_config.write({"negative_qty_block_source": "warehouse"})
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
            },
            {
                "product_id": self.wall_shelf.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
            },
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "enabled_neg_qty_tour", login="pos_user")

    def test_pos_product_sell_tour_03(self):
        """Lot-tracked product with 1 qty in the POS warehouse. Sale with the available lot is allowed."""
        self.main_pos_config.write({"negative_qty_block_source": "warehouse"})
        self.whiteboard_pen.tracking = "lot"
        lot1 = self.env["stock.lot"].create({
            "name": "lot1",
            "product_id": self.whiteboard_pen.product_variant_id.id,
        })
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot1.id,
            }
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "lot_tracked_product_success", login="pos_user")

    def test_pos_product_sell_tour_04(self):
        """Lot-tracked product with 1 qty. Sale uses an unavailable lot. Sale is blocked."""
        self.whiteboard_pen.tracking = "lot"
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": False})
        lot1 = self.env["stock.lot"].create([
            {
                "name": "lot1",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            }
        ])
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot1.id,
            },
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "lot_tracked_product_fail", login="pos_user")

    def test_pos_product_sell_tour_05(self):
        """Serial-tracked product with 2 available serials. Sale with a valid serial is allowed."""
        self.whiteboard_pen.tracking = "serial"
        lot1, lot2 = self.env["stock.lot"].create([
            {
                "name": "serial1",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            },
            {
                "name": "serial2",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            },
        ])
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot1.id,
            },
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot2.id,
            },
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "serial_tracked_product_success", login="pos_user")

    def test_pos_product_sell_tour_06(self):
        """Serial-tracked product with 2 serials in stock. Sale includes a 3rd serial with 0 stock. Sale is blocked."""
        self.whiteboard_pen.tracking = "serial"
        (self.whiteboard_pen + self.wall_shelf).write({"is_negative_pos_allowed": False})
        lot1, lot2, _lot3 = self.env["stock.lot"].create([
            {
                "name": "serial1",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            },
            {
                "name": "serial2",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            },
            {
                "name": "serial3",
                "product_id": self.whiteboard_pen.product_variant_id.id,
            },
        ])
        quants = self.env["stock.quant"].create([
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot1.id,
            },
            {
                "product_id": self.whiteboard_pen.product_variant_id.id,
                "inventory_quantity": 1,
                "location_id": self.main_pos_config.warehouse_id.pos_type_id.default_location_src_id.id,
                "lot_id": lot2.id,
            },
        ])
        quants.action_apply_inventory()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "serial_tracked_product_fail", login="pos_user")

    # ==== Settle SO on POS TESTS =====
    def test_settle_order_general_07(self):
        """SO settled on POS with stock equal to SO qty (10). Sale proceeds without a block."""
        warehouse = self.env["stock.warehouse"].create({"name": "WH-Demo", "code": "demowh"})
        product_a = self.env["product.product"].create({
            "name": "Product A",
            "available_in_pos": True,
            "type": "consu",
            "is_storable": True,
            "is_negative_pos_allowed": False,  # Default block behavior
            "lst_price": 10.0,
        })
        quants = self.env["stock.quant"].create([
            {
                "product_id": product_a.id,
                "inventory_quantity": 10,
                "location_id": warehouse.pos_type_id.default_location_src_id.id,
            }
        ])
        quants.action_apply_inventory()
        sale_order = (
            self
            .env["sale.order"]
            .sudo()
            .create({
                "partner_id": self.env["res.partner"].create({"name": "Test Partner"}).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": product_a.name,
                            "product_uom_qty": 10,
                            "price_unit": product_a.lst_price,
                        },
                    )
                ],
            })
        )
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.action_assign()
        picking.move_ids.write({"quantity": 10})
        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.assertEqual(sale_order.order_line[0].qty_in_progress, 10)

        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "block_negative_pos_settle_so_good", login="pos_user")

    def test_settle_order_with_manager_08(self):
        """SO settled exactly (skipped). Cashier adds 1 extra unit with 0 stock. Manager sees warning and proceeds."""
        self.main_pos_config.write({"advanced_employee_ids": [Command.set(self.employee_B.ids)]})
        self.main_pos_config.write({"module_pos_hr": True})
        self.env.flush_all()
        product_a = self.env["product.product"].create({
            "name": "Product A",
            "available_in_pos": True,
            "type": "consu",
            "is_storable": True,
            "is_negative_pos_allowed": False,
            "lst_price": 10.0,
        })
        sale_order = (
            self
            .env["sale.order"]
            .sudo()
            .create({
                "partner_id": self.env["res.partner"].create({"name": "Test Partner"}).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": product_a.name,
                            "product_uom_qty": 10,
                            "price_unit": product_a.lst_price,
                        },
                    )
                ],
            })
        )
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "block_negative_pos_settle_extra_warning", login="pos_user")

    def test_settle_order_with_regular_09(self):
        """SO settled exactly (skipped). Cashier adds 1 extra unit with 0 stock. Regular employee is blocked."""
        self.main_pos_config.write({"module_pos_hr": True})
        self.env.flush_all()
        product_a = self.env["product.product"].create({
            "name": "Product A",
            "available_in_pos": True,
            "type": "consu",
            "is_storable": True,
            "is_negative_pos_allowed": False,
            "lst_price": 10.0,
        })
        sale_order = (
            self
            .env["sale.order"]
            .sudo()
            .create({
                "partner_id": self.env["res.partner"].create({"name": "Test Partner"}).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": product_a.name,
                            "product_uom_qty": 10,
                            "price_unit": product_a.lst_price,
                        },
                    )
                ],
            })
        )
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "block_negative_pos_settle_extra_block", login="pos_user")
