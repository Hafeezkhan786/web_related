# -*- coding: utf-8 -*-
{
    'name': 'Custom Receipt for Customer Invoice',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Adds a custom POS-like Invoice Slip receipt report for Customer Invoices',
    'description': """
        This module adds a thermal receipt report layout for Customer Invoices (account.move),
        reusing the same POS-style receipt design used for POS Sales Slip and Delivery Slip/GDN,
        so clicking Print on a Customer Invoice generates a matching "Invoice Slip".
    """,
    'author': 'TezzTareen / PSAE Partner',
    'depends': ['account', 'web'],
    'data': [
        'reports/invoice_slip_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
