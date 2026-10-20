from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    header_note = fields.Text()
