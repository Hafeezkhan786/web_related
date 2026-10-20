# -*- coding: utf-8 -*-
from odoo import api, fields, models
from markupsafe import Markup


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    custom_seo_schema = fields.Text(
        string="Custom SEO Schema (JSON-LD)",
        help="Custom JSON-LD schema snippet to render on this eCommerce category page."
    )

    def get_seo_schema_markup(self):
        """ Return formatted custom JSON-LD Markup or False if empty """
        self.ensure_one()
        custom_schema = getattr(self.sudo(), 'custom_seo_schema', False)
        if custom_schema:
            schema_str = custom_schema.strip()
            if not schema_str:
                return False
            if schema_str.startswith('<script'):
                return Markup(schema_str)
            return Markup(f'<script type="application/ld+json">\n{schema_str}\n</script>')
        return False

    def get_faq_seo_schema_markup(self):
        """ Dynamically generate FAQPage JSON-LD Schema from category_faq HTML """
        self.ensure_one()
        faq_html = getattr(self.sudo(), 'category_faq', False)
        if not faq_html:
            return False

        if not isinstance(faq_html, str):
            faq_html = str(faq_html)

        faq_str = faq_html.strip()
        if not faq_str or faq_str in ('<p><br></p>', '<p><br/></p>', '<p></p>'):
            return False

        import json
        import re
        from markupsafe import Markup

        questions_answers = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(faq_str, 'html.parser')

            # 1. Check <details> <summary>
            details_tags = soup.find_all(['details'])
            if details_tags:
                for details in details_tags:
                    summary = details.find('summary')
                    if summary:
                        q_text = summary.get_text(strip=True)
                        summary.extract()
                        a_text = details.get_text(strip=True)
                        if q_text and a_text:
                            questions_answers.append((q_text, a_text))

            # 2. Check Accordions
            if not questions_answers:
                acc_items = soup.find_all(class_=re.compile(r'accordion-item|card'))
                if acc_items:
                    for item in acc_items:
                        header = item.find(class_=re.compile(r'accordion-header|card-header|accordion-button|btn-link'))
                        body = item.find(class_=re.compile(r'accordion-body|card-body|collapse'))
                        if header and body:
                            q_text = header.get_text(strip=True)
                            a_text = body.get_text(strip=True)
                            if q_text and a_text:
                                questions_answers.append((q_text, a_text))

            # 3. Headings & Paragraphs
            if not questions_answers:
                elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'dt', 'dd', 'li'])
                current_q = None
                current_a_parts = []

                for el in elements:
                    tag_name = el.name.lower()
                    text = el.get_text(strip=True)
                    if not text:
                        continue

                    is_q = False
                    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt']:
                        is_q = True
                    elif tag_name in ['p', 'div', 'li'] and (text.endswith('?') or text.lower().startswith(('q:', 'q.', 'faq', 'question'))):
                        is_q = True
                    elif el.find(['strong', 'b']) and (text.endswith('?') or text.lower().startswith(('q:', 'q.', 'faq', 'question'))):
                        is_q = True

                    if is_q:
                        if current_q and current_a_parts:
                            questions_answers.append((current_q, " ".join(current_a_parts)))
                            current_a_parts = []
                        current_q = text
                    else:
                        if current_q:
                            if text not in current_q:
                                current_a_parts.append(text)

                if current_q and current_a_parts:
                    questions_answers.append((current_q, " ".join(current_a_parts)))

            # 4. Fallback line parsing
            if not questions_answers:
                raw_text = soup.get_text("\n", strip=True)
                lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
                current_q = None
                current_a = []
                for line in lines:
                    if line.endswith('?') or line.lower().startswith(('q:', 'q.', 'faq', 'question')):
                        if current_q and current_a:
                            questions_answers.append((current_q, " ".join(current_a)))
                            current_a = []
                        current_q = line
                    else:
                        if current_q:
                            current_a.append(line)
                if current_q and current_a:
                    questions_answers.append((current_q, " ".join(current_a)))

        except Exception:
            pass

        if not questions_answers:
            return False

        faq_entities = []
        for q, a in questions_answers:
            q_clean = re.sub(r'^(q:|q\.|question:)\s*', '', q, flags=re.IGNORECASE).strip()
            a_clean = re.sub(r'^(a:|a\.|answer:)\s*', '', a, flags=re.IGNORECASE).strip()
            if q_clean and a_clean:
                faq_entities.append({
                    "@type": "Question",
                    "name": q_clean,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a_clean
                    }
                })

        if not faq_entities:
            return False

        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_entities
        }

        json_str = json.dumps(faq_schema, indent=2)
        return Markup(f'<script type="application/ld+json">\n{json_str}\n</script>')

