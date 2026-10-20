from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    fbr_pos_logo = fields.Binary(
        string='FBR Logo',
        help='FBR logo to be printed on receipts'
    )
