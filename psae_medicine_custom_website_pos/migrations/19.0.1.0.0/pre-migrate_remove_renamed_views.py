from odoo.upgrade.util.records import remove_view


def migrate(cr, version):
    remove_view(cr, "psae_medicine_custom_website_pos.product_price_custom")
    remove_view(cr, "psae_medicine_custom_website_pos.product_custom")
