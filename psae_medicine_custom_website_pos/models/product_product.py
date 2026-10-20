from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        product_fields = self._load_pos_data_fields(config)
        records = config.payment_method_ids.surcharge_product_id.read(product_fields, load=False)
        for record in records:
            if "taxes_id" in record:
                record["taxes_id"] = []
        return read_records + records
