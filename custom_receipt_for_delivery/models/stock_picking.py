# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api
from markupsafe import Markup


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_cleaned_note(self):
        """ Clean terms and conditions from raw non-breaking spaces and fix formatting/merging """
        if not self.note:
            return ''

        note_str = str(self.note)

        # 1. Clean encoding issues, HTML entities, and literal Â characters
        cleaned = note_str.replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ').replace('\xa0', ' ').replace('Â', '')

        # 2. Convert raw newlines (\n) to HTML line breaks (<br/>)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        lines = cleaned.split('\n')
        cleaned = '<br/>'.join(lines)

        # Clean extra spaces inside/after paragraph or break tags
        cleaned = cleaned.replace('<br/> ', '<br/>').replace('<br> ', '<br>').replace('<p> ', '<p>')

        # 3. Automatically split numbered items (e.g. 2), 3), 4)) onto new lines if merged
        for i in range(2, 15):
            pattern_space = f' {i}) '
            pattern_nb = f'\xa0{i}) '
            cleaned = cleaned.replace(pattern_space, f'<br/>{i}) ')
            cleaned = cleaned.replace(pattern_nb, f'<br/>{i}) ')

    def get_partner_phone(self):
        """ Retrieve partner phone or mobile safely without AttributeError """
        self.ensure_one()
        if not self.partner_id:
            return ''
        return getattr(self.partner_id, 'phone', False) or getattr(self.partner_id, 'mobile', False) or ''

    def change_size_page(self):
        """ Dynamically calculate accurate receipt height based on picking content and update paperformat """
        # Force update the QWeb view in the database to match our updated XML file
        # (mirrors custom_receipt_for_sale so edits to the XML take effect without a module upgrade)
        try:
            view = self.env.ref('custom_receipt_for_delivery.report_delivery_slip', raise_if_not_found=False)
            if view:
                import os
                xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'delivery_slip_report.xml')
                if os.path.exists(xml_path):
                    with open(xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()

                    start_tag = '<template id="report_delivery_slip">'
                    end_tag = '</template>'
                    if start_tag in xml_content and end_tag in xml_content:
                        template_body = xml_content.split(start_tag)[1].split(end_tag)[0]
                        new_arch = f'<template id="report_delivery_slip">{template_body}</template>'.strip()
                        if view.arch != new_arch:
                            view.sudo().write({'arch': new_arch})
        except Exception:
            pass

        paper_format = self.env.ref('custom_receipt_for_delivery.paperformat_delivery_slip', raise_if_not_found=False)
        if not paper_format:
            paper_format = self.env['report.paperformat'].search([('name', '=', 'Delivery Slip Paper Format')], limit=1)

        if not paper_format:
            return ''

        max_height = 90  # Minimum base height in mm

        for picking in self:
            # 1. Base Header, Company, Details & Footer height (in mm)
            base_height = 65

            if picking.company_id.logo:
                base_height += 15

            # Customer / delivery address details
            if picking.partner_id:
                base_height += 4.5
                if picking.partner_id.street:
                    base_height += 4.5
                if picking.partner_id.street2:
                    base_height += 4.5
                if picking.get_partner_phone():
                    base_height += 4.5

            if picking.origin:
                base_height += 4.5

            sale_order = picking.sale_id
            if sale_order and sale_order.team_id:
                base_height += 4.5
            if sale_order and sale_order.user_id:
                base_height += 4.5

            # 2. Product Lines height
            lines_height = 0
            moves = picking.move_ids.filtered(lambda m: m.product_id)
            for move in moves:
                line_h = 6.0  # Base product line height in mm
                name_len = len(move.product_id.name or '')
                # 13px font size on 54mm width fits approx 20 chars per line in the product name column
                if name_len > 20:
                    extra_lines = math.ceil((name_len - 20) / 20.0)
                    line_h += extra_lines * 4.5

                lines_height += line_h

            # 3. Notes (doc.note) height
            note_height = 0
            if picking.note:
                clean_note = picking.get_cleaned_note()
                clean_note = clean_note.replace('<p>', '').replace('</p>', '\n').replace('<br/>', '\n').replace('<br>', '\n')
                lines = [l for l in clean_note.split('\n') if l.strip()]
                note_lines_count = 0
                for l in lines:
                    note_lines_count += math.ceil(len(l) / 32.0) if len(l) > 0 else 1
                note_height = note_lines_count * 3.5 + 6

            picking_total_height = base_height + lines_height + note_height
            if picking_total_height > max_height:
                max_height = picking_total_height

        # Add 5mm safety buffer at bottom
        final_height = int(math.ceil(max_height + 5))

        paper_format.sudo().write({
            'page_height': final_height
        })
        return ''
