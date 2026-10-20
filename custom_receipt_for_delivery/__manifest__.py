{
    'name': 'Custom Receipt for Delivery Order',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Adds a custom POS-like Delivery Slip report for Delivery Orders (stock.picking)',
    'description': """
        This module adds a thermal receipt report layout for Delivery Orders,
        reusing the same POS-style receipt design used for the Sale Slip report,
        so clicking Print on a Delivery Order (WH/OUT/...) generates a matching
        "Delivery Slip".
    """,
    'author': 'TezzTareen / PSAE Partner',
    'depends': ['stock', 'sale_stock', 'web'],
    'data': [
        'reports/delivery_slip_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
