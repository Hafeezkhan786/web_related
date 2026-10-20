{
    "name": "PSAE Mr. Medicine Mart - Custom Website & PoS",
    "summary": "Custom checkout logic, medical product fields, and POS receipt adjustments",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "version": "19.0.1.0.0",
    "license": "OEEL-1",
    "depends": ["website_sale_stock", "pos_loyalty"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/uom_uom_views.xml",
        "views/address_templates.xml",
        "views/payment_form_templates.xml",
        "views/templates.xml",
        "views/product_template_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/product_public_category_views.xml",
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "psae_medicine_custom_website_pos/static/src/scss/regulatory_dropdown.scss",
            "psae_medicine_custom_website_pos/static/src/interactions/*.js",
            "psae_medicine_custom_website_pos/static/src/js/*/*.js",
            # Must load before website_sale.js: that file does
            # `Object.assign(WebsiteSale.prototype, VariantMixin)` at module-eval
            # time, copying the mixin methods by value. A patch applied after
            # that runs never reaches the interaction prototype. Same directive
            # Odoo uses for website_sale_stock_wishlist.
            (
                "before",
                "website_sale/static/src/interactions/website_sale.js",
                "psae_medicine_custom_website_pos/static/src/js/variant_mixin.js",
            ),
        ],
        "point_of_sale._assets_pos": [
            "psae_medicine_custom_website_pos/static/src/app/**/*",
        ],
    },
    "task_ids": [5410113, 5985581, 6216261, 6264243, 6264270, 6264298, 6264841, 6264933, 6300452, 6300496, 6319562],
}
