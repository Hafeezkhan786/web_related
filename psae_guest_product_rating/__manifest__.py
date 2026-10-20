# -*- coding: utf-8 -*-
{
    'name': 'PSAE - Guest Visitor Product Star Rating',
    'summary': 'Allows guest/visitor customers to submit 1-5 star ratings and reviews with email verification without login',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'author': 'PSAE',
    'depends': ['website_sale', 'rating'],
    'data': [
        'views/rating_rating_views.xml',
        'views/portal_rating_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'psae_guest_product_rating/static/src/js/guest_rating_modal.js',
            'psae_guest_product_rating/static/src/scss/guest_rating_modal.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
