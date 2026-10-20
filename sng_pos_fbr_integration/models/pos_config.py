from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    fbr_pos_integration = fields.Boolean(
        string='Enable FBR POS Integration',
        help='Enable integration with FBR POS system for invoice generation'
    )
    fbr_pos_url = fields.Char(
        string='FBR POS URL',
        help='URL of the FBR POS API endpoint'

    )
    fbr_pos_token = fields.Char(
        string='FBR POS Token',
        help='Authentication token for FBR POS API'
    )
    fbr_pos_timeout = fields.Integer(
        string='FBR POS Timeout (seconds)',
        default=10,
        help='Timeout for FBR POS API requests'
    )
    
    # Testing specific fields
    fbr_pos_id = fields.Char(
        string='FBR POS ID',
        help='POS ID for testing environment'
    )
    fbr_branch_code = fields.Char(
        string='FBR Branch Code',
        help='Branch code for testing environment'
    )
    fbr_environment = fields.Selection([
        ('testing', 'Testing'),
        ('production', 'Production'),
    ], string='FBR Environment', default='testing')
    
    # Production specific fields
    fbr_production_url = fields.Char(
        string='FBR Production URL',
        help='Production URL of the FBR POS API endpoint'
    )
    fbr_production_token = fields.Char(
        string='FBR Production Token',
        help='Production authentication token for FBR POS API'
    )
