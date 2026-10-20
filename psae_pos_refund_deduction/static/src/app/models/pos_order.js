import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this._refundDeductionApplied) {
            data.is_refund_deduction = true;
        }
        return data;
    },
});
