# -*- coding: utf-8 -*-
from odoo import models, api, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_approved_rating_stats(self):
        self.ensure_one()
        ratings = self.get_approved_ratings()
        total_count = len(ratings)
        counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        percent = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        if not total_count:
            return {
                'avg': 0.0,
                'avg_display': '0',
                'count': 0,
                'counts': counts,
                'percent': percent,
            }
        
        total_sum = sum(r.rating for r in ratings)
        avg = round(total_sum / total_count, 1)
        avg_display = str(int(avg)) if avg == int(avg) else str(avg)
        
        for r in ratings:
            val = int(round(r.rating))
            if 1 <= val <= 5:
                counts[val] += 1
                
        for star in range(1, 6):
            percent[star] = round((counts[star] / total_count) * 100)
            
        return {
            'avg': avg,
            'avg_display': avg_display,
            'count': total_count,
            'counts': counts,
            'percent': percent,
        }

    def get_approved_ratings(self):
        self.ensure_one()
        return self.env['rating.rating'].sudo().search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', self.id),
            ('is_approved', '=', True),
            ('consumed', '=', True),
        ], order='create_date desc')
