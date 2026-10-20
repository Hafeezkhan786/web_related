# -*- coding: utf-8 -*-
{
    'name': 'Inventory Replenishment Enhancement',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add delivered quantity fields to replenishment list view',
    'author': 'PSAE',
    'depends': ['stock'],
    'data': [
        'views/stock_warehouse_orderpoint_views.xml',
    ],
    'installable': True,
    'application': False,
}
