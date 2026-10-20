from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    has_surcharge = fields.Boolean("Surcharge")
    surcharge_percent = fields.Float()
    surcharge_product_id = fields.Many2one("product.product", domain=[("type", "=", "service")])

    @api.constrains("surcharge_percent")
    def _check_surcharge_percent(self):
        for method in self:
            if method.has_surcharge and (
                float_compare(method.surcharge_percent, 0, precision_digits=2) <= 0
                or float_compare(method.surcharge_percent, 1, precision_digits=2) > 0
            ):
                raise ValidationError(_("Surcharge Percent must be between 0 and 100 when Surcharge is enabled."))

    @api.model
    def _load_pos_data_fields(self, config):
        res = super()._load_pos_data_fields(config)
        return res + ["has_surcharge", "surcharge_percent", "surcharge_product_id"]
