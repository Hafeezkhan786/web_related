from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_auto_add_product_ids = fields.Many2many(
        'product.product',
        string="Auto Add Products on Website Cart",
        help="Products that will be automatically added to the cart when this product is added.",
        domain="[('sale_ok', '=', True), ('type', '!=', 'service')]"
    )
    website_auto_add_pkg_qty = fields.Integer(
        string="Auto Add Packaging Qty",
        default=0,
        help="Packaging capacity rule. E.g. 5 means 1 auto-added item for every 5 units (1 to 5 = 1, 6 to 10 = 2, 11 to 15 = 3, etc.). If 0, 1:1 ratio is used."
    )
