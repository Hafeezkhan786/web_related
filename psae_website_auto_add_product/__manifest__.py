{
    'name': 'Website Auto Add Product',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Automatically add related products to cart',
    'description': """
        This module allows configuration on product template to automatically add 
        other products to the cart when the main product is added.
    """,
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
