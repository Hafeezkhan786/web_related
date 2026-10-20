# -*- coding: utf-8 -*-
from odoo import api, fields, models
from markupsafe import Markup


class WebsitePage(models.Model):
    _inherit = "website.page"

    custom_seo_schema = fields.Text(
        string="Custom SEO Schema (JSON-LD)",
        help="Custom JSON-LD schema snippet to render on this website page."
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

    def get_dynamic_seo_schema_markup(self, request_url="", website=None):
        """ Generate dynamic JSON-LD WebPage / Organization Schema for website pages """
        self.ensure_one()
        import json
        from markupsafe import Markup

        page_name = self.name or self.title or "Website Page"
        url = request_url or ""
        company_name = (website and website.company_id and website.company_id.name) or "Mr Medicine Mart"
        logo_url = (website and website.image_url(website, 'logo')) or ""

        # Homepage check
        is_homepage = (self.url in ['/', '/home']) or (self.url and self.url.strip('/') == '')

        if is_homepage:
            schema_data = {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "Organization",
                        "@id": f"{url}#organization" if url else "#organization",
                        "name": company_name,
                        "url": url or "https://www.mrmedicinemart.com/",
                        "logo": logo_url
                    },
                    {
                        "@type": "WebSite",
                        "@id": f"{url}#website" if url else "#website",
                        "url": url or "https://www.mrmedicinemart.com/",
                        "name": company_name,
                        "publisher": {
                            "@id": f"{url}#organization" if url else "#organization"
                        }
                    },
                    {
                        "@type": "WebPage",
                        "@id": f"{url}#webpage" if url else "#webpage",
                        "url": url,
                        "name": page_name,
                        "isPartOf": {
                            "@id": f"{url}#website" if url else "#website"
                        }
                    }
                ]
            }
        else:
            schema_data = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": page_name,
                "url": url,
                "description": f"{page_name} - {company_name}"
            }

        json_str = json.dumps(schema_data, indent=2)
        return Markup(json_str)
