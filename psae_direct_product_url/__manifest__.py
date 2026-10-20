{
    'name': 'PSAE - Direct Product Canonical URLs on Category Pages',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Ensures category page product cards link directly to canonical product URLs without category slug prefixes.',
    'description': """
PSAE Direct Product Canonical URLs
==================================
Overrides the product item QWeb template on category pages so that all product card links 
use direct canonical product URLs (/shop/product-slug) instead of category-prefixed URLs 
(/shop/category-slug/product-slug).
""",
    'author': 'System Nexgen / PSAE',
    'depends': ['website_sale'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
