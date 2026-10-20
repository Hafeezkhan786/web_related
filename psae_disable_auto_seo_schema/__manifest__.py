{
    'name': 'PSAE - SEO Schema Management & All-Rounder Page Schemas',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Manages SEO Schema markup for products, website pages, categories, and brand pages.',
    'description': """
SEO Schema Management (All-Rounder)
==================================
Provides full SEO JSON-LD schema management:
1. Automatic @graph Product Schema for all 8000+ products.
2. Custom SEO Schema backend overrides for any Website Page (website.page).
3. Custom SEO Schema backend overrides for any eCommerce Category (product.public.category).
4. Custom SEO Schema backend overrides for Products (product.template).
""",
    'author': 'System Nexgen / PSAE',
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
        'views/website_page_views.xml',
        'views/category_views.xml',
        'views/seo_schema_templates.xml',
        'data/disable_schema_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
