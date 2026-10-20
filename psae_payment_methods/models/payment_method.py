from odoo import _, fields, models

from odoo.addons.payment import utils as payment_utils


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    supported_state_ids = fields.Many2many("res.country.state", string="States")

    def _get_compatible_payment_methods(self, provider_ids, partner_id, currency_id=None, force_tokenization=False, is_express_checkout=False, report=None, **kwargs):  # fmt:skip
        payment_methods = super()._get_compatible_payment_methods(provider_ids, partner_id, currency_id=currency_id, force_tokenization=force_tokenization, is_express_checkout=is_express_checkout, report=report, **kwargs)  # fmt:skip
        # On website/portal checkout filter on the delivery address state (carried via
        # sale_order_id), falling back to the partner's own state outside that context.
        order = self.env["sale.order"].browse(sale_order_id) if (sale_order_id := kwargs.get("sale_order_id")) else None
        if state := (order.partner_shipping_id.state_id if order else self.env["res.partner"].browse(partner_id).state_id):  # fmt:skip
            excluded = payment_methods.filtered(lambda pm: pm.supported_state_ids and state not in pm.supported_state_ids)  # fmt:skip
            payment_utils.add_to_report(report, excluded, available=False, reason=_("incompatible state"))
            payment_methods -= excluded
        return payment_methods
