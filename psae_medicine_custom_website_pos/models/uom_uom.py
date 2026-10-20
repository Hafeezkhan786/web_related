from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    website_uom_label = fields.Html(string="Website UoM Label")
    medical_packaging_id = fields.Many2one("medicine.packaging.type")
