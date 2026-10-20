# -*- coding: utf-8 -*-
import re
from odoo import http
from odoo.http import request

class GuestProductRatingController(http.Controller):

    @http.route(['/website/guest_rating/post'], type='jsonrpc', auth='public', website=True, csrf=False)
    def post_guest_rating(self, product_id, rating, name=None, email=None, feedback=None, **kw):
        if not product_id:
            return {'error': 'Product ID is missing.'}

        try:
            product_id = int(product_id)
            rating_val = float(rating)
        except (ValueError, TypeError):
            return {'error': 'Invalid product or rating parameter.'}

        if rating_val < 1.0 or rating_val > 5.0:
            return {'error': 'Please select a star rating (1 to 5 stars).'}

        clean_comment = (feedback or '').strip()
        if not clean_comment:
            return {'error': 'Please write your review comment.'}

        clean_name = (name or '').strip()
        if not clean_name:
            return {'error': 'Please enter your name.'}

        clean_email = (email or '').strip().lower()
        if not clean_email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', clean_email):
            return {'error': 'Please enter a valid email address.'}

        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return {'error': 'Product not found.'}

        # Check 1 review per email per product rule to prevent duplicate / spam reviews
        existing = request.env['rating.rating'].sudo().search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', product_id),
            ('partner_id.email', '=', clean_email)
        ], limit=1)

        if existing:
            return {'error': 'A review has already been submitted using this email address for this product.'}

        # Find or create partner for the given email
        partner = request.env['res.partner'].sudo().search([
            ('email', '=', clean_email)
        ], limit=1)

        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': clean_name,
                'email': clean_email,
            })
        elif clean_name and (partner.name == clean_email or not partner.name):
            partner.sudo().write({'name': clean_name})

        # Create pending rating (is_approved = False, requires Admin Approval)
        model_id = request.env['ir.model'].sudo()._get('product.template').id
        request.env['rating.rating'].sudo().create({
            'res_model_id': model_id,
            'res_model': 'product.template',
            'res_id': product_id,
            'rating': rating_val,
            'partner_id': partner.id,
            'feedback': clean_comment,
            'is_approved': False,
            'consumed': True,
        })

        return {
            'success': True,
            'message': 'Thank you! Your review has been submitted and is pending admin approval.'
        }
