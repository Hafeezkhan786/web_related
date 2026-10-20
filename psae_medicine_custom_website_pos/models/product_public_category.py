from odoo import fields, models


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    category_faq = fields.Html(
        string="FAQ",
        sanitize_attributes=False,
        sanitize_form=False,
        translate=True,
    )
