# -*- coding: utf-8 -*-
import re
from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'

    search_prioritize_relevance = fields.Boolean(
        string='Prioritize Exact Name Matches in Search',
        default=True,
        help='When enabled, products whose name starts with or contains the search term '
             'will appear at the top of the search suggestions and shop results.'
    )
    search_exclude_descriptions = fields.Boolean(
        string='Exclude Descriptions from Search',
        default=False,
        help='When enabled, search queries will only match product names and internal references, '
             'ignoring text in sales and e-commerce descriptions.'
    )

    def _search_with_fuzzy(self, search_type, search, limit, order, options):
        """
        Overrides website search to enforce relevance-based ranking.
        Fetches a wider pool when limit is small (e.g. autocomplete) so that exact name
        matches aren't cut off by alphabetical database ordering before relevance ranking.
        """
        # If relevance sorting is disabled in settings, fall back to standard behavior
        if not self.search_prioritize_relevance:
            return super()._search_with_fuzzy(search_type, search, limit, order, options)

        # If a limit is applied (e.g. autocomplete limit=5), expand the fetch limit
        # so SQL query doesn't discard relevant name matches that occur later alphabetically
        expanded_limit = (limit * 5) if (limit and limit <= 20) else limit

        count, results, fuzzy_term = super()._search_with_fuzzy(
            search_type, search, expanded_limit, order, options
        )

        effective_term = (fuzzy_term or search or '').strip().lower()
        if not effective_term or not results:
            return count, results, fuzzy_term

        # Re-sort results for each model (primarily product.template)
        for res_dict in results:
            records = res_dict.get('results')
            if not records or not hasattr(records, 'sorted'):
                continue

            # Calculate relevance score for each record
            def get_relevance_score(rec):
                name = (rec.name or '').strip().lower()
                code = (getattr(rec, 'default_code', '') or '').strip().lower()

                # Score 0: Exact name match
                if name == effective_term:
                    return (0, name)

                # Score 1: Name starts with search term (e.g., "Panadol 500mg Tablet")
                if name.startswith(effective_term):
                    return (1, name)

                # Score 2: Search term is a whole word in the product name
                if re.search(r'\b' + re.escape(effective_term) + r'\b', name):
                    return (2, name)

                # Score 3: Search term is a substring in the product name
                if effective_term in name:
                    return (3, name)

                # Score 4: Matches default_code / SKU
                if code and (code == effective_term or code.startswith(effective_term)):
                    return (4, name)

                # Score 5: Matched only through description / generic / other fields
                return (5, name)

            # Sort records by relevance tier first, then alphabetically by name
            sorted_records = records.sorted(key=get_relevance_score)

            # Slice back to the originally requested limit (e.g. 5 for dropdown)
            if limit:
                sorted_records = sorted_records[:limit]

            res_dict['results'] = sorted_records

        return count, results, fuzzy_term
