{
    'name': 'Custom Receipt for Sale Order',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Adds a custom POS-like receipt report for Sales Orders',
    'description': """
        This module adds a thermal receipt report layout for Sales Orders,
        reusing the POS receipt design (Design 2) format.
    """,
    'author': 'TezzTareen / PSAE Partner',
    'depends': ['sale', 'web'],
    'data': [
        'reports/sale_slip_report.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
