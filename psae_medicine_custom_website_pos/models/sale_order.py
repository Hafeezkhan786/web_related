import math

from odoo import models
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _verify_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        """Override to enforce `allowed_ecommerce_qty` on cart updates.

        For regular products, Odoo merges repeated additions into the same line,
        so `new_qty` is always the running total for that line and a single
        comparison against `allowed_ecommerce_qty` is sufficient.

        For combo products, each addition always creates a new sale order line
        because linked sub-item lines prevent merging. As a result, `new_qty`
        only reflects the quantity being added in the current request, not the
        cumulative total. Without aggregating existing lines, a customer could
        bypass `allowed_ecommerce_qty` by splitting purchases across multiple
        additions (e.g. adding 5 + 5 + 5 to bypass a limit of 10).

        To close this gap, when the product is a combo we query the total
        quantity already in the cart for that product template (excluding the
        current line) and subtract it from `allowed_ecommerce_qty` to compute
        the true remaining allowance before applying the cap.
        """
        new_qty, warning = super()._verify_updated_quantity(order_line, product_id, new_qty, uom_id, **kwargs)
        product = self.env["product.product"].browse(product_id)
        if not product:
            return new_qty, warning

        selected_uom = self.env["uom.uom"].browse(uom_id) if uom_id else product.uom_id
        selected_name = (selected_uom.name or "").lower()
        is_box = "box" in selected_name
        is_strip = "strip" in selected_name and not is_box
        allowed = product.allowed_ecommerce_qty
        if allowed and selected_uom and product.uom_id:
            if is_box:
                units_per_box = max(selected_uom._compute_quantity(1.0, product.uom_id), 3.0)
                allowed = max(math.floor(allowed / units_per_box), 0)
            elif selected_uom != product.uom_id:
                try:
                    base_units_per_target = selected_uom._compute_quantity(1.0, product.uom_id)
                    if base_units_per_target > 0:
                        allowed = max(math.floor(allowed / base_units_per_target), 0)
                except Exception:
                    pass

        if not allowed:
            return new_qty, warning

        if product.type == "combo":
            result = dict(
                self.env["sale.order.line"]._read_group(
                    domain=(
                        Domain("order_id", "=", self.id)
                        & Domain("product_id.product_tmpl_id", "=", product.product_tmpl_id.id)
                        & Domain("id", "not in", order_line.ids)
                    ),
                    groupby=["order_id"],
                    aggregates=["product_uom_qty:sum"],
                )
            )
            allowed = max(allowed - (result.get(self) or 0), 0)

        if new_qty > allowed:
            new_qty = allowed
            if is_box:
                warning = f"Aap {int(allowed)} box se ziyada order nahi kar saktay. (Maximum {int(allowed)} Boxes allowed per order)"
            elif is_strip:
                warning = f"Aap {int(allowed)} strip se ziyada order nahi kar saktay. (Maximum {int(allowed)} Strips allowed per order)"
            else:
                warning = f"Limit exceeded. You can only purchase {int(allowed)} of {product.name}."
        return new_qty, warning
