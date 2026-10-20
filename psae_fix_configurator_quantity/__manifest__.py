{
    "name": "PSAE - Fix Product Configurator Quantity Check (isQuantityAllowed)",
    "summary": "Hotfix for 'product.isQuantityAllowed is not a function' Owl error "
               "in the website product configurator dialog",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "version": "19.0.1.0.0",
    "license": "OEEL-1",
    "depends": ["website_sale", "psae_medicine_custom_website_pos"],
    "data": [],
    "assets": {
        "web.assets_frontend": [
            (
                "after",
                "psae_medicine_custom_website_pos/static/src/js/product_configurator_dialog/product_configurator_dialog.js",
                "psae_fix_configurator_quantity/static/src/js/product_configurator_dialog/product_configurator_dialog.js",
            ),
        ],
    },
}
