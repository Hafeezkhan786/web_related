# -*- coding: utf-8 -*-
{
    'name': 'PSAE - Purchase Order Custom Line Fields',
    'summary': 'Adds On Hand Qty, Min/Max Rules, Previous 2 Months Sale, and Current Month Sale columns to Purchase Order lines',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'author': 'PSAE',
    'depends': ['purchase', 'purchase_stock'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
