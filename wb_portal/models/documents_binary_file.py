# -*- coding: utf-8 -*-
from odoo import fields, models


class DocumentsBinary(models.Model):
    """Small extension of documents.document used by the employee portal."""
    _inherit = 'documents.document'

    binary_file = fields.Binary('Binary File')
