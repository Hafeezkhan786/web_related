# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    custom_seo_schema = fields.Text(
        string="Custom SEO Schema (JSON-LD)",
        help="Custom JSON-LD schema snippet to override automatic dynamic product schema for this product."
    )

    def get_seo_schema_markup(self):
        """ Return formatted custom JSON-LD Markup or False if empty """
        self.ensure_one()
        custom_schema = getattr(self.sudo(), 'custom_seo_schema', False)
        if custom_schema:
            schema_str = custom_schema.strip()
            if not schema_str:
                return False
            from markupsafe import Markup
            if schema_str.startswith('<script'):
                return Markup(schema_str)
            return Markup(f'<script type="application/ld+json">\n{schema_str}\n</script>')
        return False

    def get_dynamic_seo_schema_markup(self, request_url="", currency_code="PKR", image_url=""):
        """ Generate dynamic JSON-LD Product Schema Markup using @graph structure for all products """
        self.ensure_one()
        import json
        import re
        from markupsafe import Markup

        product_sudo = self.sudo()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')

        prod_name = product_sudo.name or ""
        prod_desc = product_sudo.description_sale or product_sudo.name or ""
        if prod_desc and ('<' in prod_desc and '>' in prod_desc):
            prod_desc = re.sub(r'<[^>]+>', ' ', prod_desc).strip()

        prod_sku = product_sudo.default_code or str(product_sudo.id)
        prod_brand = product_sudo.company_id.name or "Mr Medicine Mart"
        prod_barcode = product_sudo.barcode or False

        prod_category = "General"
        if hasattr(product_sudo, 'public_categ_ids') and product_sudo.public_categ_ids:
            prod_category = product_sudo.public_categ_ids[0].name
        elif product_sudo.categ_id:
            prod_category = product_sudo.categ_id.name

        # Combination price calculation
        price_val = product_sudo.list_price
        try:
            if hasattr(product_sudo, '_get_combination_info'):
                combination_info = product_sudo._get_combination_info()
                price_val = combination_info.get('price', product_sudo.list_price)
        except Exception:
            pass

        # Availability check
        qty_avail = getattr(product_sudo, 'qty_available', 1)
        prod_avail = "InStock" if (qty_avail is None or qty_avail > 0) else "OutOfStock"

        # Canonical absolute product URL
        prod_website_url = getattr(product_sudo, 'website_url', False)
        if prod_website_url:
            canonical_url = f"{base_url}{prod_website_url}"
        else:
            canonical_url = request_url or base_url

        # All product images (ensure absolute URLs starting with http/https)
        images = []
        if image_url:
            full_img_url = image_url if image_url.startswith('http') else f"{base_url}{image_url}"
            images.append(full_img_url)
        else:
            images.append(f"{base_url}/web/image/product.template/{product_sudo.id}/image_1920")

        if hasattr(product_sudo, 'product_template_image_ids') and product_sudo.product_template_image_ids:
            for img in product_sudo.product_template_image_ids:
                img_path = f"{base_url}/web/image/product.image/{img.id}/image_1920"
                if img_path not in images:
                    images.append(img_path)

        product_dict = {
            "@type": "Product",
            "@id": f"{canonical_url}#product",
            "name": prod_name,
            "image": images,
            "description": prod_desc,
            "sku": str(prod_sku),
            "brand": {
                "@type": "Brand",
                "name": prod_brand
            },
            "category": prod_category,
            "url": canonical_url,
            "offers": {
                "@type": "Offer",
                "url": canonical_url,
                "priceCurrency": currency_code or "PKR",
                "price": f"{float(price_val):.2f}",
                "availability": f"https://schema.org/{prod_avail}",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {
                    "@type": "Organization",
                    "name": prod_brand
                }
            }
        }
        if prod_barcode:
            product_dict["gtin"] = str(prod_barcode)
            product_dict["barcode"] = str(prod_barcode)

        # Rating if available (safely accessed with sudo and exception handling)
        try:
            rating_count = getattr(product_sudo, 'rating_count', 0)
            if rating_count and rating_count > 0:
                rating_avg = getattr(product_sudo, 'rating_avg', 5.0)
                product_dict["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": str(rating_avg),
                    "reviewCount": str(rating_count)
                }
        except Exception:
            pass

        schema_data = {
            "@context": "https://schema.org",
            "@graph": [product_dict]
        }

        json_str = json.dumps(schema_data, indent=2)
        return Markup(json_str)
