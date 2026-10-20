# -*- coding: utf-8 -*-
from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _search_get_detail(self, website, order, options):
        """
        Customize search details to ensure search fields and fuzzy search fields
        are optimized for relevance.
        """
        res = super()._search_get_detail(website, order, options)

        # Check website settings or option flags
        exclude_descriptions = getattr(website, 'search_exclude_descriptions', False)

        if exclude_descriptions:
            # Exclude descriptions from search fields to match only name & code
            res['search_fields'] = [
                f for f in res.get('search_fields', [])
                if f not in ('description', 'description_sale', 'description_ecommerce')
            ]

        # For Odoo 16/17/18: optimize fuzzy_search_fields to prevent broad descriptions
        # from diluting typo-matching on Odoo.sh with pg_trgm enabled
        if 'fuzzy_search_fields' in res:
            res['fuzzy_search_fields'] = ['name', 'default_code']

        return res
