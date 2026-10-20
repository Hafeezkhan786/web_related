from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    phone = fields.Char(string='Phone', compute='_compute_phone', store=False)

    @api.depends('res_model', 'res_id')
    def _compute_phone(self):
        for activity in self:
            phone = False
            if activity.res_model and activity.res_id:
                record = self.env[activity.res_model].browse(activity.res_id).sudo()
                if record.exists():
                    def _get_phone(rec):
                        p = getattr(rec, 'phone', False)
                        if p:
                            return p
                        m = getattr(rec, 'mobile', False)
                        if m:
                            return m
                        return False

                    phone = _get_phone(record)
                    if not phone and getattr(record, 'partner_id', False):
                        phone = _get_phone(record.partner_id)
            activity.phone = phone

