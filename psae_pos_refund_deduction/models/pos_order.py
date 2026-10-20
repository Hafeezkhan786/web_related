# -*- coding: utf-8 -*-
from odoo import models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_refund_deduction = fields.Boolean(
        string='2% Refund Deduction Applied',
        default=False,
        readonly=True,
        help='Indicates whether a 2% deduction was applied during refund.'
    )
