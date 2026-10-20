import math

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    should_restrict_website_sale = fields.Boolean(string="Restrict Sale On Website")
    allowed_ecommerce_qty = fields.Integer()

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        product_fields = self._load_pos_data_fields(config)
        records = config.payment_method_ids.surcharge_product_id.product_tmpl_id.read(product_fields, load=False)
        for record in records:
            if "taxes_id" in record:
                record["taxes_id"] = []
        return read_records + records

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, uom, date, website)
        target_uom = self.env["uom.uom"].browse(uom) if isinstance(uom, int) else (uom or self.uom_id)
        allowed = self.allowed_ecommerce_qty
        if allowed and target_uom and self.uom_id:
            target_name = (target_uom.name or "").lower()
            is_box = "box" in target_name
            if is_box:
                units_per_box = max(target_uom._compute_quantity(1.0, self.uom_id), 3.0)
                allowed = max(math.floor(allowed / units_per_box), 0)
            elif target_uom != self.uom_id:
                try:
                    base_units_per_target = target_uom._compute_quantity(1.0, self.uom_id)
                    if base_units_per_target > 0:
                        allowed = max(math.floor(allowed / base_units_per_target), 0)
                except Exception:
                    pass
        res["allowed_ecommerce_qty"] = allowed
        res["prevent_zero_price_sale"] = True if self.should_restrict_website_sale else res.get("prevent_zero_price_sale", False)  # fmt:skip
        # Resolve the UoM display labels here so the public website templates
        # render them without sudo: public visitors lack read access on uom.uom
        # and the custom medical packaging model, so we sudo the reads and pass
        # plain strings.
        product_uom = target_uom.sudo()
        res["uom_per_label"] = product_uom.medical_packaging_id.name or product_uom.name
        res["website_uom_label"] = product_uom.website_uom_label
        return res

    @api.model
    def _get_additional_configurator_data(self, product_or_template, date, currency, pricelist, *, uom=None, **kwargs):
        data = super()._get_additional_configurator_data(product_or_template, date, currency, pricelist, uom=uom, **kwargs)  # fmt:skip
        if product_or_template.allowed_ecommerce_qty:
            allowed = product_or_template.allowed_ecommerce_qty
            template = product_or_template if isinstance(product_or_template, models.Model) and product_or_template._name == "product.template" else product_or_template.product_tmpl_id
            target_uom = self.env["uom.uom"].browse(uom) if isinstance(uom, int) else (uom or template.uom_id)
            if target_uom and template.uom_id:
                target_name = (target_uom.name or "").lower()
                is_box = "box" in target_name
                if is_box:
                    units_per_box = max(target_uom._compute_quantity(1.0, template.uom_id), 3.0)
                    allowed = max(math.floor(allowed / units_per_box), 0)
                elif target_uom != template.uom_id:
                    try:
                        base_units_per_target = target_uom._compute_quantity(1.0, template.uom_id)
                        if base_units_per_target > 0:
                            allowed = max(math.floor(allowed / base_units_per_target), 0)
                    except Exception:
                        pass
            data["allowed_ecommerce_qty"] = allowed
        return data
