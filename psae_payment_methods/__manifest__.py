{
    "name": "PSAE Payment Methods",
    "version": "19.0.1.0.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": ["sale", "payment"],
    "data": [
        "views/payment_method_views.xml",
        "views/payment_provider_views.xml",
        "views/sale_order_views.xml",
        "reports/ir_actions_report_templates.xml",
    ],
    "task_ids": [5106567, 5985581],
}
