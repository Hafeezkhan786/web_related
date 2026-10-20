from odoo.upgrade.util.specific import reset_cowed_views


def migrate(cr, version):
    reset_cowed_views(cr, "website_sale.product")
    reset_cowed_views(cr, "website_sale.ecom_show_extra_fields")
    reset_cowed_views(cr, "website_sale.alternative_products")
