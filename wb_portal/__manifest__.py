# -*- coding: utf-8 -*-
{
    'name': 'WB HR Employee Portal',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Modern employee self-service portal: dashboard, attendance, planning, payslips, time off, expenses, loans, news, events and documents',
    'description': """
WB HR Employee Portal
=====================

A modern, self-service HR portal for employees, upgraded for **Odoo 18**.

Features
--------
* **Dashboard** (/home/): profile hero, attendance stats, leave balances and approval history
* **Attendance** (/attendance/): monthly calendar, filterable history, PDF export and geo check-in/out
* **Planning** (/planning/): weekly / monthly shift view (native `planning` module, Enterprise)
* **Payslips** (/payslip/): filterable payslip list, detail view and PDF download
* **Time Off** (/leaveform/): request time off, view my requests, approve / refuse for managers
* **Expenses** (/expenses/): view own expenses and create / submit new ones (`hr_expense`)
* **Loans** (/loans/): view own loans and apply for new ones (`wb.loan`, or an existing `hr.loan`)
* **Announcements** (/announcements/): company news from a Discuss channel (`discuss.channel`)
* **Events** (/events/): upcoming events (native `event` module)
* **Documents** (/documents/): upload and download personal documents
* **Notifications**: bell center + browser notifications for time off, attendance, etc.
* **Theming**: per-user presets + admin theme module (`wb_portal_theme`)
* **Automatic numbering**: leave requests (TS/DD/MM/XXX) and loans (LN/YYYY/NNNN)

Notes for Odoo 18
-----------------
* `documents` and `planning` are **Enterprise only** in Odoo 18 - both are hard
  dependencies (along with `event` and `hr_expense`), so this module installs on
  Odoo 18 Enterprise. On Community, remove those two from `depends` (and the
  pages degrade gracefully via a friendly message when their models are absent).
* `hr_payroll` (payslips) is Enterprise only; the payslip pages degrade gracefully.
""",
    'author': 'WB',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'website',
        'portal',
        'hr',
        'hr_attendance',
        'hr_holidays',
        'documents',      # Odoo Enterprise
        'planning',       # Odoo Enterprise
        'helpdesk',       # Odoo Enterprise
        'event',
        'hr_payroll',
        'hr_expense',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/wb_portal_security.xml',
        'data/sequence_gen.xml',
        'data/report/attendance_report.xml',
        'data/report/Attendance_report_template.xml',
        'views/sequence_gen.xml',
        'views/work_location_views.xml',
        'views/attendance_views.xml',
        'views/email_template.xml',
        'views/website_menus.xml',
        'views/loan_views.xml',
        'views/portal_template.xml',
        'views/portal_extras.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'wb_portal/static/src/js/portal.js',
            'wb_portal/static/src/scss/wb_portal.scss',
        ],
    },
    'installable': True,
}
