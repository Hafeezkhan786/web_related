from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_in_progress = fields.Float(compute="_compute_qty_in_progress", digits="Product Unit of Measure", store=True)

    @api.depends("move_ids.state", "move_ids.location_dest_usage", "move_ids.quantity", "move_ids.product_uom")
    def _compute_qty_in_progress(self):
        """
        Quantity reserved (assigned) by the SO's outgoing stock moves but not yet delivered.

        When a cashier settles an SO in POS, the linked delivery moves are still in state
        'assigned' — the reserved stock has not been released yet. At the moment of the POS
        stock check, that reserved qty is therefore not reflected in free_qty. Without
        subtracting it, the POS would see lower available stock than what will actually be
        freed once the POS order is validated, causing false blocks on legitimate settlements.

        This field is loaded into the POS session so the JS layer can compute the true
        delta: delta = pos_line_qty - qty_in_progress. Only the delta is sent to
        check_quantity, so already-reserved SO quantities are never double-counted.

        Adapted from sale_stock._compute_qty_delivered.
        """
        for line in self:
            if line.qty_delivered_method != "stock_move":
                continue
            qty_in_progress = 0.0
            outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
            for move in outgoing_moves:
                if move.state == "assigned":
                    qty_in_progress += move.product_uom._compute_quantity(
                        move.quantity, line.product_uom_id, rounding_method="HALF-UP"
                    )
            for move in incoming_moves:
                if move.state == "assigned":
                    qty_in_progress -= move.product_uom._compute_quantity(
                        move.quantity, line.product_uom_id, rounding_method="HALF-UP"
                    )
            line.qty_in_progress = qty_in_progress

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["qty_in_progress"]
