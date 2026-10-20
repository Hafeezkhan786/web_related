from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_type_id = fields.Many2one("payment.method", compute="_compute_payment_type_id", store=True)

    @api.depends("transaction_ids")
    def _compute_payment_type_id(self):
        for order in self:
            order.payment_type_id = order.transaction_ids[:1].payment_method_id
