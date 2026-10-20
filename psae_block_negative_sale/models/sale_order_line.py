from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, **kwargs):
        """Block procurement launch when any storable line has insufficient stock.

        Calls ``super()`` first so moves are created and ``free_qty_today`` is
        correctly populated, then raises ``UserError`` if stock is insufficient —
        rolling back the entire transaction.

        Fires on both initial confirm and confirmed-SO line additions. Skipped for
        users in ``group_allow_negative_sale``.

        :raises UserError: If ``free_qty_today < qty_to_deliver`` on any storable line
            with pending delivery.
        """
        result = super()._action_launch_stock_rule(**kwargs)
        if not self.env.user.has_group("psae_block_negative_sale.group_allow_negative_sale") and any(
            line.display_qty_widget
            and float_compare(line.free_qty_today, line.qty_to_deliver, precision_rounding=line.product_uom_id.rounding) < 0
            for line in self
        ):  # fmt: skip
            raise UserError(_("Oops! Not enough stock. Check the forecast view on the order lines for more details."))
        return result
