# -*- coding: utf-8 -*-
{
    'name': 'PSAE | POS Refund 2% Deduction',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add -2% deduction button on POS payment screen for refund orders',
    'description': """
        POS Refund 2% Deduction
        ========================
        Adds a '-2%' button on the POS payment screen when an order is being refunded.
        Clicking the button deducts 2% from the total refund amount.
    """,
    'author': 'PSAE',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'psae_pos_refund_deduction/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
