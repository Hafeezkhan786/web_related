{
    'name': 'POS FBR Integration',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Integrates POS orders with FBR system for invoice generation and printing',
    'description': """
        POS FBR Integration Module
        
        This module integrates POS orders with FBR (Federal Board of Revenue) system to:
        - Automatically send POS order data to FBR POS on payment
        - Retrieve FBR invoice numbers
        - Print FBR invoice numbers and logos on POS receipts
        - Handle FBR integration errors and retries
        
        Features:
        - Real-time FBR invoice generation
        - Automatic data synchronization with FBR POS
        - Enhanced receipt printing with FBR branding
        - Error handling and retry mechanisms
    """,
    'author': 'HUNAIN SHEIKH SNG',
    'website': 'https://tezztareen.com/',
    'depends': ['point_of_sale', 'product', 'stock', 'base'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/cron_data.xml',
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
        'views/res_company_view.xml',
        'reports/pos_fbr_receipt.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'sng_pos_fbr_integration/static/src/js/pos_fbr_models.js',
            'sng_pos_fbr_integration/static/src/xml/pos_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
