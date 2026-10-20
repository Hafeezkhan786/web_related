# -*- coding: utf-8 -*-
{
    'name': 'Website Search Relevance & Priority',
    'version': '1.0.0',
    'category': 'eCommerce',
    'summary': 'Fixes search result ranking and prioritizes exact product name matches over descriptions in website search autocomplete and shop page.',
    'description': """
Website Search Relevance & Priority
===================================
This module fixes the issue where irrelevant products (e.g. Actifed, Flueze) appear before 
the exact searched product (e.g. Panadol) in the website search suggestions.

Key Features:
-------------
* **Smart Relevance Sorting**: Ranks exact name matches first, followed by SKU matches, and lastly description/generic matches.
* **Fuzzy Search Optimization**: Fixes Odoo.sh pg_trgm fuzzy matching to avoid description pollution in suggestions.
* **Autocomplete & Shop Support**: Works seamlessly on both the header search autocomplete dropdown and the main /shop catalog.
* **Fully Compatible**: Supports Odoo 15.0, 16.0, 17.0, and 18.0 on Odoo.sh and on-premise deployments.
    """,
    'author': 'Custom Development',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
