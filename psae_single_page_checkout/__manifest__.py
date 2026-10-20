{
    "name": "PSAE Single Page Checkout",
    "summary": "Unified single-page checkout flow inspired by Naheed.pk",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "version": "19.0.1.0.0",
    "license": "OEEL-1",
    "depends": ["sale", "website_sale", "website_sale_stock", "sale_management", "website_sale_collect"],
    "data": [
        "views/single_checkout_templates.xml",
        'views/confirmation_template_inherit.xml',
    ],
    "assets": {
        "web.assets_frontend": [
            "psae_single_page_checkout/static/src/scss/single_checkout.scss",
            "psae_single_page_checkout/static/src/js/single_checkout.js",
        ],
    },
}
