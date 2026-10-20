# -*- coding: utf-8 -*-
import math
import re
from odoo import models, fields, api
from markupsafe import Markup


class AccountMove(models.Model):
    _inherit = 'account.move'

    def format_amount(self, amount):
        """ Format monetary amounts with comma separators """
        try:
            val = float(amount or 0.0)
            if abs(val - round(val)) < 0.0001:
                return "{:,.0f}".format(val)
            return "{:,.2f}".format(val)
        except Exception:
            return "0"

    def get_sales_order_ref(self):
        """ Retrieve linked sales order or POS order reference name """
        self.ensure_one()
        if self.invoice_origin:
            return self.invoice_origin
        try:
            so_names = self.line_ids.sale_line_ids.order_id.mapped('name')
            if so_names:
                return ', '.join(set(so_names))
        except Exception:
            pass
        if hasattr(self, 'pos_order_ids') and self.pos_order_ids:
            return ', '.join(self.pos_order_ids.mapped('name'))
        return ''

    def get_invoice_datetime_display(self):
        """ Format Invoice Date & Time using invoice_date and create_date time if available """
        self.ensure_one()
        if self.create_date:
            local_dt = fields.Datetime.context_timestamp(self, self.create_date)
            if not self.invoice_date or self.invoice_date == local_dt.date():
                return local_dt.strftime('%d-%m-%Y %H:%M:%S')
            else:
                time_str = local_dt.strftime('%H:%M:%S')
                return f"{self.invoice_date.strftime('%d-%m-%Y')} {time_str}"
        elif self.invoice_date:
            return self.invoice_date.strftime('%d-%m-%Y')
        return ''

    def get_payment_status_display(self):
        """ Get standard clean payment status (PAID, PARTIAL, PENDING) """
        self.ensure_one()
        state = self.payment_state or 'not_paid'
        if state in ('paid', 'in_payment'):
            return 'PAID'
        elif state == 'partial':
            return 'PARTIAL'
        elif state == 'not_paid':
            return 'PENDING'
        elif state == 'reversed':
            return 'REVERSED'
        return state.upper()

    def get_customer_display_info(self):
        """ Retrieve formatted customer and contact person details """
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return {
                'customer_name': '',
                'contact_person': '',
                'phone': '',
                'street': '',
                'street2': '',
                'city': '',
                'state': '',
                'ref': '',
            }

        # If partner has parent company, parent is customer and partner is contact person
        if partner.parent_id:
            cust_name = partner.parent_id.name
            contact_person = partner.name
        else:
            cust_name = partner.name
            contact_person = ''

        phone = partner.phone or partner.mobile or ''
        if not phone and partner.parent_id:
            phone = partner.parent_id.phone or partner.parent_id.mobile or ''

        return {
            'customer_name': cust_name,
            'contact_person': contact_person,
            'phone': phone,
            'street': partner.street or '',
            'street2': partner.street2 or '',
            'city': partner.city or '',
            'state': partner.state_id.name if partner.state_id else '',
            'ref': partner.ref or '',
        }

    def get_formatted_billing_address(self):
        """ Return formatted single-string billing address """
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return ''
        addr_parts = []
        if partner.street:
            addr_parts.append(partner.street.strip())
        if partner.street2:
            addr_parts.append(partner.street2.strip())
        city_state = []
        if partner.city:
            city_state.append(partner.city.strip())
        if partner.state_id:
            city_state.append(partner.state_id.name.strip())
        if city_state:
            addr_parts.append(', '.join(city_state))
        if partner.ref:
            addr_parts.append(partner.ref.strip())
        return ', '.join(addr_parts)

    def get_cleaned_note(self):
        """ Clean terms & conditions from raw non-breaking spaces, garbled characters and fix formatting """
        raw_note = self.narration or ''
        if not raw_note:
            return ''

        note_str = str(raw_note)

        # 1. Fix UTF-8 / Windows-1252 corrupted characters (e.g. â€™ -> ', â€˜ -> ', â€œ / â€ -> ")
        note_str = note_str.replace('weâ€™re', "we're")
        note_str = note_str.replace('â€™', "'")
        note_str = note_str.replace('â€˜', "'")
        note_str = note_str.replace('â€œ', '"')
        note_str = note_str.replace('â€', '"')
        note_str = note_str.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')

        # 2. Remove garbled symbols, box drawing characters, and repetitive divider lines
        cleaned = re.sub(r'[â\u2500-\u257F\u2010-\u2015─━]+', '', note_str)
        cleaned = cleaned.replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ').replace('\xa0', ' ').replace('Â', '')

        # Clean specific garbled artifact patterns
        cleaned = re.sub(r'â["”]?€[â["”]?€]*', '', cleaned)
        cleaned = re.sub(r'─+', '', cleaned)
        cleaned = re.sub(r'-{3,}', '', cleaned)
        cleaned = re.sub(r'={3,}', '', cleaned)

        # 3. Convert raw newlines (\n) to HTML line breaks (<br/>)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
        cleaned = '<br/>'.join(lines)

        # Clean extra spaces inside/after paragraph or break tags
        cleaned = cleaned.replace('<br/> ', '<br/>').replace('<br> ', '<br>').replace('<p> ', '<p>')

        # 4. Strip any leading "Terms and Conditions:" from the note body (including any HTML tags wrapping it)
        cleaned = re.sub(r'^(?:<[^>]+>|\s*|&nbsp;)*(?:terms\s+and\s+conditions:?)(?:<[^>]+>|\s*|&nbsp;|<br/?>)*', '', cleaned, flags=re.IGNORECASE)

        # 5. Automatically split numbered items (e.g. 1), 2), 3), 4)) onto new lines if merged
        for i in range(1, 15):
            cleaned = re.sub(rf'(?<!^)(?<!<br/>)(?<!<br>)(?:\s+|&nbsp;|\xa0)({i}\))', r'<br/>\1', cleaned)

        return Markup(cleaned.strip())

    def change_size_page(self):
        """ Dynamically calculate accurate receipt height based on invoice content and update paperformat """
        # Force update the QWeb view in the database to match our updated XML file
        try:
            view = self.env.ref('custom_receipt_for_invoice.report_invoice_slip', raise_if_not_found=False)
            if view:
                import os
                xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'invoice_slip_report.xml')
                if os.path.exists(xml_path):
                    with open(xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()

                    start_tag = '<template id="report_invoice_slip">'
                    end_tag = '</template>'
                    if start_tag in xml_content and end_tag in xml_content:
                        template_body = xml_content.split(start_tag)[1].split(end_tag)[0]
                        new_arch = f'<template id="report_invoice_slip">{template_body}</template>'.strip()
                        if view.arch != new_arch:
                            view.sudo().write({'arch': new_arch})
        except Exception:
            pass

        paper_format = self.env.ref('custom_receipt_for_invoice.paperformat_invoice_slip', raise_if_not_found=False)
        if not paper_format:
            paper_format = self.env['report.paperformat'].search([('name', '=', 'Invoice Slip Paper Format')], limit=1)

        if not paper_format:
            return ''

        max_height = 100  # Minimum base height in mm

        for invoice in self:
            # 1. Base Header, Company, Details, Totals, QR Code & Footer height (in mm)
            base_height = 105

            if invoice.company_id.logo:
                base_height += 25

            # Customer details
            cust_info = invoice.get_customer_display_info()
            if cust_info['customer_name']:
                base_height += 5.5
            if cust_info['contact_person']:
                base_height += 5.5
            if cust_info['phone']:
                base_height += 5.5
            if invoice.get_formatted_billing_address():
                addr_len = len(invoice.get_formatted_billing_address())
                base_height += math.ceil(addr_len / 25.0) * 5.0

            if invoice.get_sales_order_ref():
                base_height += 5.5
            if invoice.ref:
                base_height += 5.5
            if invoice.payment_reference and invoice.payment_reference != invoice.name and invoice.payment_reference != invoice.ref:
                base_height += 5.5
            if invoice.team_id:
                base_height += 5.5
            if invoice.invoice_user_id or invoice.user_id:
                base_height += 5.5
            if invoice.invoice_payment_term_id:
                base_height += 5.5

            # 2. Invoice Lines height
            lines_height = 0
            lines = invoice.invoice_line_ids.filtered(lambda l: (not l.display_type or l.display_type == 'product') and l.product_id)
            for line in lines:
                line_h = 7.5  # Base line height
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

            # 3. Terms & Conditions (doc.narration) height
            note_height = 0
            if invoice.narration:
                clean_note = invoice.get_cleaned_note()
                clean_note = clean_note.replace('<p>', '').replace('</p>', '\n').replace('<br/>', '\n').replace('<br>', '\n')
                note_lines = [l for l in clean_note.split('\n') if l.strip()]
                note_lines_count = 0
                for l in note_lines:
                    note_lines_count += math.ceil(len(l) / 30.0) if len(l) > 0 else 1
                note_height = note_lines_count * 3.8 + 10

            invoice_total_height = base_height + lines_height + note_height
            if invoice_total_height > max_height:
                max_height = invoice_total_height

        # Add 8mm safety buffer at bottom
        final_height = int(math.ceil(max_height + 8))

        paper_format.sudo().write({
            'page_height': final_height
        })
        return ''


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_line_description(self):
        """ Extract custom description / note for line, excluding product name duplicate """
        self.ensure_one()
        desc = ''
        if self.name and self.product_id:
            prod_name = self.product_id.display_name or self.product_id.name or ''
            name_val = self.name.strip()
            if name_val != prod_name.strip():
                if name_val.startswith(prod_name):
                    desc = name_val[len(prod_name):].strip(' \t\r\n-:\n')
                else:
                    desc = name_val
        elif self.name:
            desc = self.name.strip()

        if not desc and self.product_id and hasattr(self.product_id, 'description_sale') and self.product_id.description_sale:
            desc = self.product_id.description_sale.strip()
        return desc
