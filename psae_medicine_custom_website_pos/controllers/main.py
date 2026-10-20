from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.website import Website
from odoo import http
from odoo.http import request
from textwrap import shorten
from odoo.tools import html_escape as escape
import re


class WebsiteSaleCustom(WebsiteSale):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)
        field_names.discard("email")
        return field_names

    def _get_mandatory_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_address_fields(country_sudo)
        field_names.discard("zip")
        return field_names

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_delivery_address_fields(country_sudo)
        field_names.discard("email")
        return field_names

    def _validate_address_values(self, address_values, partner_sudo, address_type, use_delivery_as_billing, required_fields, **_kwargs):  # fmt:skip
        address_values.update({"email": partner_sudo.email or address_values.get("email"), "zip": partner_sudo.zip or address_values.get("zip")})  # fmt:skip
        return super()._validate_address_values(address_values, partner_sudo, address_type, use_delivery_as_billing, required_fields, **_kwargs)  # fmt:skip


class WebsiteCustomSearch(Website):

    @http.route('/website/snippet/autocomplete', type='jsonrpc', auth='public', website=True, readonly=True)
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        order = self._get_search_order(order)
        options = options or {}
        if 'display_currency' not in options:
            options['display_currency'] = request.website.currency_id
        results_count, search_results, fuzzy_term = request.website._search_with_fuzzy(search_type, term, limit, order, options)
        if not results_count:
            return {
                'results': [],
                'results_count': 0,
                'parts': {},
            }
        term = fuzzy_term or term
        search_results = request.website._search_render_results(search_results, limit)

        mappings = []
        results_data = []
        for search_result in search_results:
            for r in search_result['results_data']:
                r['_model'] = search_result['model']
            results_data += search_result['results_data']
            mappings.append(search_result['mapping'])

        if search_type in ('all', None) or not search_type:
            results_data.sort(key=lambda r: r.get('name', ''), reverse='name desc' in order)
            results_data.sort(key=lambda r: 0 if r.get('_model') == 'product.template' else 1)

        results_data = results_data[:limit]
        result = []
        for record in results_data:
            mapping = record['_mapping']
            mapped = {
                '_fa': record.get('_fa'),
            }
            for mapped_name, field_meta in mapping.items():
                value = record.get(field_meta.get('name'))
                if not value:
                    mapped[mapped_name] = ''
                    continue
                field_type = field_meta.get('type')
                if field_type == 'text':
                    if value and field_meta.get('truncate', True):
                        value = shorten(value, max_nb_chars, placeholder='...')
                    if field_meta.get('match') and value and term:
                        pattern = '|'.join(map(re.escape, term.split()))
                        if pattern:
                            parts = re.split(f'({pattern})', value, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                value = request.env['ir.ui.view'].sudo()._render_template(
                                    "website.search_text_with_highlight",
                                    {'parts': parts}
                                )
                                field_type = 'html'

                if field_type not in ('image', 'binary') and ('ir.qweb.field.%s' % field_type) in request.env:
                    opt = {}
                    if field_type == 'monetary':
                        opt['display_currency'] = options['display_currency']
                    value = request.env[('ir.qweb.field.%s' % field_type)].value_to_html(value, opt)
                mapped[mapped_name] = escape(value)
            result.append(mapped)

        return {
            'results': result,
            'results_count': results_count,
            'parts': {key: True for mapping in mappings for key in mapping},
            'fuzzy_search': fuzzy_term,
        }

