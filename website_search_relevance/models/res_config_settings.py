# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    search_prioritize_relevance = fields.Boolean(
        related='website_id.search_prioritize_relevance',
        readonly=False,
        string='Prioritize Exact Name Matches in Search'
    )
    search_exclude_descriptions = fields.Boolean(
        related='website_id.search_exclude_descriptions',
        readonly=False,
        string='Exclude Product Descriptions from Search'
    )
