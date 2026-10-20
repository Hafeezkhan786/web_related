from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    custom_mobile = fields.Char("Mobile (Whatsapp)")

    def _get_frontend_writable_fields(self):
        writable_fields = super()._get_frontend_writable_fields()
        writable_fields.add("custom_mobile")
        return writable_fields
