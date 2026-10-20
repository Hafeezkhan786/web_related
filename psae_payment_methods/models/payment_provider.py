from odoo import _, api, fields, models

from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    available_state_ids = fields.Many2many("res.country.state", string="States")

    @api.model
    def _get_compatible_providers(self, company_id, partner_id, amount, currency_id=None, force_tokenization=False, is_express_checkout=False, is_validation=False, report=None, **kwargs):  # fmt:skip
        providers = super()._get_compatible_providers(company_id, partner_id, amount, currency_id=currency_id, force_tokenization=force_tokenization, is_express_checkout=is_express_checkout, is_validation=is_validation, report=report, **kwargs)  # fmt:skip
        # On website/portal checkout filter on the delivery address state (carried via
        # sale_order_id), falling back to the partner's own state outside that context.
        order = self.env["sale.order"].browse(sale_order_id) if (sale_order_id := kwargs.get("sale_order_id")) else None
        if state := (order.partner_shipping_id.state_id if order else self.env["res.partner"].browse(partner_id).state_id):  # fmt:skip
            excluded = providers.filtered(lambda p: p.available_state_ids and state not in p.available_state_ids)
            payment_utils.add_to_report(report, excluded, available=False, reason=_("incompatible state"))
            providers -= excluded
        return providers
