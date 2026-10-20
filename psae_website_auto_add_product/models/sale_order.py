from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_auto_added = fields.Boolean(
        string="Is Auto Added",
        default=False,
        help="Technical flag indicating this line was automatically added."
    )


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _calculate_auto_add_qty(self, qty: float, pkg: int) -> int:
        qty = int(qty)
        if qty <= 0:
            return 0
        if pkg and pkg > 0:
            if qty % pkg:
                return int(qty / pkg) + 1
            else:
                return int(qty / pkg)
        return qty

    def _sync_auto_add_products(self):
        """
        Synchronize auto-added packaging products based on cart contents
        and product packaging rules.
        """
        if self.env.context.get('skip_auto_add'):
            return

        order = self.with_context(skip_auto_add=True)

        needed_quantities = {}
        configured_auto_product_ids = set()

        for line in order.order_line:
            if getattr(line, 'is_delivery', False) or getattr(line, 'is_auto_added', False):
                continue
            if line.product_uom_qty <= 0 or not line.product_id:
                continue

            template = line.product_id.product_tmpl_id
            if not template or not template.website_auto_add_product_ids:
                continue

            pkg = template.website_auto_add_pkg_qty or 0
            req_qty = self._calculate_auto_add_qty(line.product_uom_qty, pkg)

            for auto_prod in template.website_auto_add_product_ids:
                configured_auto_product_ids.add(auto_prod.id)
                needed_quantities[auto_prod.id] = needed_quantities.get(auto_prod.id, 0) + req_qty

        # All existing auto-added lines in this order
        existing_auto_lines = order.order_line.filtered(lambda l: l.is_auto_added)

        # Adopt any line for configured auto products that was created earlier without the flag
        for auto_prod_id in configured_auto_product_ids:
            if not existing_auto_lines.filtered(lambda l: l.product_id.id == auto_prod_id):
                unflagged_line = order.order_line.filtered(
                    lambda l: l.product_id.id == auto_prod_id and not l.is_auto_added
                )[:1]
                if unflagged_line:
                    unflagged_line.write({'is_auto_added': True})
                    existing_auto_lines |= unflagged_line

        # Update or create lines for needed auto products
        for auto_prod_id, needed_qty in needed_quantities.items():
            line = existing_auto_lines.filtered(lambda l: l.product_id.id == auto_prod_id)[:1]
            if line:
                if needed_qty > 0:
                    if line.product_uom_qty != needed_qty:
                        line.write({'product_uom_qty': needed_qty})
                else:
                    line.unlink()
            else:
                if needed_qty > 0:
                    order._cart_add(
                        product_id=auto_prod_id,
                        quantity=needed_qty,
                        uom_id=None,
                    )
                    new_line = order.order_line.filtered(
                        lambda l: l.product_id.id == auto_prod_id and not l.is_auto_added
                    )[:1]
                    if new_line:
                        new_line.write({'is_auto_added': True})

        # Remove auto-added lines that are no longer needed
        for line in existing_auto_lines:
            if line.exists() and (line.product_id.id not in needed_quantities or needed_quantities[line.product_id.id] <= 0):
                line.unlink()

        if not self.env.context.get('skip_cart_verification'):
            order._verify_cart_after_update()

    def _cart_add(self, product_id: int, quantity: float = 1.0, *, uom_id: int | None = None, **kwargs) -> dict:
        res = super()._cart_add(product_id=product_id, quantity=quantity, uom_id=uom_id, **kwargs)
        if not self.env.context.get('skip_auto_add'):
            self._sync_auto_add_products()
        return res

    def _cart_update_line_quantity(self, line_id: int, quantity: float, **kwargs) -> dict:
        res = super()._cart_update_line_quantity(line_id=line_id, quantity=quantity, **kwargs)
        if not self.env.context.get('skip_auto_add'):
            self._sync_auto_add_products()
        return res
