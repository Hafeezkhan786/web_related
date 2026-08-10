# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrLeaveSequence(models.Model):
    """Auto-number every time off request with the WB portal sequence."""
    _inherit = 'hr.leave'

    sequence = fields.Char(string='Leave Code', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence'):
                vals['sequence'] = self.env['ir.sequence'].next_by_code(
                    'wb_portal.leave.sequence')
        return super().create(vals_list)
