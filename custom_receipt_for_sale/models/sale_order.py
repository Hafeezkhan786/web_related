# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api
from markupsafe import Markup

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_print_sale_slip(self):
        """ Print Sale Slip report directly from dedicated header button """
        self.ensure_one()
        return self.env.ref('custom_receipt_for_sale.action_report_sale_slip').report_action(self)

    def format_amount(self, amount):
        """ Format monetary amounts with comma separators """
        try:
            val = float(amount or 0.0)
            if abs(val - round(val)) < 0.0001:
                return "{:,.0f}".format(val)
            return "{:,.2f}".format(val)
        except Exception:
            return "0"

    def get_payment_info(self):
        """ Retrieve Payment Method and Online Payment Method if applicable """
        self.ensure_one()
        pay_method = self.payment_term_id.name if self.payment_term_id else ''
        online_pay_method = ''

        if hasattr(self, 'payment_type_id') and self.payment_type_id:
            online_pay_method = self.payment_type_id.name
        elif self.transaction_ids:
            tx = self.transaction_ids.filtered(lambda t: t.state in ('done', 'authorized'))[:1] or self.transaction_ids[:1]
            if tx.payment_method_id:
                online_pay_method = tx.payment_method_id.name
            elif tx.provider_id:
                online_pay_method = tx.provider_id.name

        return {
            'payment_method': pay_method,
            'online_payment_method': online_pay_method,
        }

    def get_source_medium_display(self):
        """ Retrieve formatted Source / Medium string if set """
        self.ensure_one()
        res = []
        if hasattr(self, 'source_id') and self.source_id:
            res.append(self.source_id.display_name or self.source_id.name or str(self.source_id))
        elif hasattr(self, 'source') and self.source:
            res.append(str(self.source))

        if hasattr(self, 'medium_id') and self.medium_id:
            res.append(self.medium_id.display_name or self.medium_id.name or str(self.medium_id))
        elif hasattr(self, 'medium') and self.medium:
            res.append(str(self.medium))

        return ' / '.join(res) if res else ''

    def get_cleaned_note(self):
        """ Clean terms and conditions from raw non-breaking spaces, garbled characters and fix formatting """
        if not self.note:
            return ''
        
        import re
        note_str = str(self.note)
        
        # 1. Remove garbled symbols, box drawing characters, and repetitive divider lines
        cleaned = re.sub(r'[â\u2500-\u257F\u2010-\u2015─━]+', '', note_str)
        cleaned = cleaned.replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ').replace('\xa0', ' ').replace('Â', '')
        
        # Clean specific garbled artifact patterns
        cleaned = re.sub(r'â["”]?€[â["”]?€]*', '', cleaned)
        cleaned = re.sub(r'─+', '', cleaned)
        cleaned = re.sub(r'-{3,}', '', cleaned)
        cleaned = re.sub(r'={3,}', '', cleaned)
        
        # 2. Convert raw newlines (\n) to HTML line breaks (<br/>)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
        cleaned = '<br/>'.join(lines)
        
        # Clean extra spaces inside/after paragraph or break tags
        cleaned = cleaned.replace('<br/> ', '<br/>').replace('<br> ', '<br>').replace('<p> ', '<p>')
        
        # 3. Automatically split numbered items (e.g. 2), 3), 4)) onto new lines if merged
        for i in range(2, 15):
            pattern_space = f' {i}) '
            pattern_nb = f'\xa0{i}) '
            cleaned = cleaned.replace(pattern_space, f'<br/>{i}) ')
            cleaned = cleaned.replace(pattern_nb, f'<br/>{i}) ')
            
        return Markup(cleaned.strip())

    def change_size_page(self):
        """ Dynamically calculate accurate receipt height based on order content and update paperformat """
        # Force update the QWeb view in the database to match our updated XML file
        try:
            view = self.env.ref('custom_receipt_for_sale.report_sale_slip', raise_if_not_found=False)
            if view:
                import os
                xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'sale_slip_report.xml')
                if os.path.exists(xml_path):
                    with open(xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    
                    start_tag = '<template id="report_sale_slip">'
                    end_tag = '</template>'
                    if start_tag in xml_content and end_tag in xml_content:
                        template_body = xml_content.split(start_tag)[1].split(end_tag)[0]
                        new_arch = f'<template id="report_sale_slip">{template_body}</template>'.strip()
                        if view.arch != new_arch:
                            view.sudo().write({'arch': new_arch})
        except Exception as e:
            pass

        paper_format = self.env.ref('custom_receipt_for_sale.paperformat_sale_slip', raise_if_not_found=False)
        if not paper_format:
            paper_format = self.env['report.paperformat'].search([('name', '=', 'Sale Slip Paper Format')], limit=1)
        
        if not paper_format:
            return ''

        max_height = 100  # Minimum base height in mm

        for order in self:
            # Write debug note to inspect exact characters
            try:
                import os
                debug_path = os.path.join(os.path.dirname(__file__), 'debug_note.txt')
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(repr(order.note))
            except Exception as e:
                pass

            # 1. Base Header, Company, Totals, QR Code & Footer height (in mm)
            base_height = 80
            
            if order.company_id.logo:
                base_height += 25
            
            # Customer details
            if order.partner_id:
                base_height += 4.5
                if order.partner_id.street:
                    base_height += 4.5
                if order.partner_id.street2:
                    base_height += 4.5

            if order.client_order_ref:
                base_height += 4.5

            if order.team_id:
                base_height += 4.5

            if order.get_source_medium_display():
                base_height += 4.5

            pay_info = order.get_payment_info()
            if pay_info['payment_method']:
                base_height += 4.5
            if pay_info['online_payment_method']:
                base_height += 4.5

            # 2. Order Lines height
            lines_height = 0
            for line in order.order_line:
                if line.display_type:
                    lines_height += 5.5
                else:
                    line_h = 7.5  # Base product line height in mm (product name line + pricing detail line)
                    name_len = len(line.product_id.name or '')
                    # 12px font size on 54mm width fits approx 16 chars per line in the product name column
                    if name_len > 16:
                        extra_lines = math.ceil((name_len - 16) / 16.0)
                        line_h += extra_lines * 4.5
                    
                    if line.discount > 0:
                        line_h += 2.0
                    
                    desc = line.get_line_description()
                    if desc:
                        line_h += math.ceil(len(desc) / 20.0) * 4.0

                    lines_height += line_h

            # 3. Terms & Conditions (doc.note) height
            note_height = 0
            if order.note:
                clean_note = order.get_cleaned_note()
                # Remove HTML tag markers to count actual text lengths
                clean_note = clean_note.replace('<p>', '').replace('</p>', '\n').replace('<br/>', '\n').replace('<br>', '\n')
                lines = [l for l in clean_note.split('\n') if l.strip()]
                note_lines_count = 0
                for l in lines:
                    # 10px font size on 54mm width fits approx 32 chars per line
                    note_lines_count += math.ceil(len(l) / 32.0) if len(l) > 0 else 1
                note_height = note_lines_count * 3.5 + 6

            order_total_height = base_height + lines_height + note_height
            if order_total_height > max_height:
                max_height = order_total_height

        # Add 5mm safety buffer at bottom
        final_height = int(math.ceil(max_height + 5))

        paper_format.sudo().write({
            'page_height': final_height
        })
        return ''

    def change_size_page_blank(self):
        """ Dynamically calculate accurate receipt height for Blank Slip and update paperformat """
        try:
            view = self.env.ref('custom_receipt_for_sale.report_blank_slip', raise_if_not_found=False)
            if view:
                import os
                xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'sale_slip_report.xml')
                if os.path.exists(xml_path):
                    with open(xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    
                    start_tag = '<template id="report_blank_slip">'
                    end_tag = '</template>'
                    if start_tag in xml_content and end_tag in xml_content:
                        template_body = xml_content.split(start_tag)[1].split(end_tag)[0]
                        new_arch = f'<template id="report_blank_slip">{template_body}</template>'.strip()
                        if view.arch != new_arch:
                            view.sudo().write({'arch': new_arch})
        except Exception as e:
            pass

        paper_format = self.env.ref('custom_receipt_for_sale.paperformat_blank_slip', raise_if_not_found=False)
        if not paper_format:
            paper_format = self.env['report.paperformat'].search([('name', '=', 'Blank Slip Paper Format')], limit=1)
        
        if not paper_format:
            return ''

        max_height = 50  # Minimum base height in mm for blank slip

        for order in self:
            base_height = 25
            
            if order.partner_id:
                base_height += 4.5
                if order.partner_id.street:
                    base_height += 4.5
                if order.partner_id.street2:
                    base_height += 4.5

            if order.client_order_ref:
                base_height += 4.5

            if order.team_id:
                base_height += 4.5

            if order.get_source_medium_display():
                base_height += 4.5

            pay_info = order.get_payment_info()
            if pay_info['payment_method']:
                base_height += 4.5
            if pay_info['online_payment_method']:
                base_height += 4.5

            lines_height = 0
            for line in order.order_line:
                if line.display_type:
                    lines_height += 5.5
                else:
                    line_h = 7.5
                    name_len = len(line.product_id.name or '')
                    if name_len > 16:
                        extra_lines = math.ceil((name_len - 16) / 16.0)
                        line_h += extra_lines * 4.5
                    
                    if line.discount > 0:
                        line_h += 2.0

                    desc = line.get_line_description()
                    if desc:
                        line_h += math.ceil(len(desc) / 20.0) * 4.0

                    lines_height += line_h

            order_total_height = base_height + lines_height
            if order_total_height > max_height:
                max_height = order_total_height

        final_height = int(math.ceil(max_height + 5))

        paper_format.sudo().write({
            'page_height': final_height
        })
        return ''


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def get_line_description(self):
        """ Extract custom quotation/description for line, excluding product name duplicate """
        self.ensure_one()
        desc = ''
        if self.name and self.product_id:
            prod_name = self.product_id.display_name or self.product_id.name or ''
            name_val = self.name.strip()
            if name_val != prod_name.strip():
                if name_val.startswith(prod_name):
                    desc = name_val[len(prod_name):].strip(' \t\r\n-:')
                else:
                    desc = name_val
        elif self.name:
            desc = self.name.strip()

        if not desc and self.product_id and hasattr(self.product_id, 'description_sale') and self.product_id.description_sale:
            desc = self.product_id.description_sale.strip()
        return desc

