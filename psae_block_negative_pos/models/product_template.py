from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_negative_pos_allowed = fields.Boolean(tracking=True, copy=False, help="Allows Negative Moves in POS.")
