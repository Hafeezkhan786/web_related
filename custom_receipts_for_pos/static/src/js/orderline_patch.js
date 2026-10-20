/** @odoo-module */
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    get lineScreenValues() {
        const vals = super.lineScreenValues;
        const line = this.line;
        
        // Add UOM to name if it exists
        if (line.product_id?.uom_id?.name && vals.name) {
            vals.name = `${vals.name} (${line.product_id.uom_id.name})`;
        }
        
        return vals;
    }
});
