# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class RatingRating(models.Model):
    _inherit = 'rating.rating'

    is_approved = fields.Boolean(
        string="Is Approved",
        default=False,
        help="If checked, this product review is published and visible on the website."
    )

    def action_approve(self):
        for rec in self:
            rec.is_approved = True
            if not rec.message_id and rec.res_model == 'product.template' and rec.res_id:
                product = self.env['product.template'].sudo().browse(rec.res_id)
                if product.exists():
                    msg = self.env['mail.message'].sudo().create({
                        'model': 'product.template',
                        'res_id': rec.res_id,
                        'body': rec.feedback or _("Rating: %s Stars") % int(rec.rating),
                        'rating_id': rec.id,
                        'author_id': rec.partner_id.id if rec.partner_id else False,
                        'message_type': 'comment',
                        'subtype_id': self.env.ref('mail.mt_comment').id,
                    })
                    rec.message_id = msg.id

    def action_reject(self):
        for rec in self:
            rec.is_approved = False
            if rec.message_id:
                rec.message_id.sudo().unlink()
