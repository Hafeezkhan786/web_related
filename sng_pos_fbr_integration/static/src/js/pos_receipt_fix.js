/** @odoo-module **/
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        
        // Always include FBR data in receipt
        result.fbr_invoice_number = this.fbr_invoice_number || "";
        result.fbr_status = this.fbr_status || "draft";
        result.fbr_error_message = this.fbr_error_message || "";
        
        return result;
    },
});
