import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.refundDeductionState = useState({
            applied: Boolean(this.currentOrder?._refundDeductionApplied),
        });
    },

    get isRefundOrder() {
        return Boolean(
            super.isRefundOrder ||
            this.currentOrder?.isRefund ||
            (this.currentOrder?.lines && this.currentOrder.lines.some((l) => l.refunded_orderline_id || l.qty < 0)) ||
            (this.currentOrder && this.currentOrder.totalDue < 0)
        );
    },

    get isDeductionApplied() {
        return Boolean(this.refundDeductionState?.applied);
    },

    toggleDeduction() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }

        const apply = !this.refundDeductionState.applied;
        this.refundDeductionState.applied = apply;
        order._refundDeductionApplied = apply;

        if (apply) {
            for (const line of order.lines) {
                if (line._orig_discount_refund === undefined) {
                    line._orig_discount_refund = line.discount || 0;
                }
                const d0 = line._orig_discount_refund;
                // Net refund reduction of 2%:
                // (1 - d_new / 100) = (1 - d0 / 100) * 0.98
                // d_new = 100 - (100 - d0) * 0.98 = d0 * 0.98 + 2
                const newDiscount = d0 * 0.98 + 2;
                line.setDiscount(newDiscount);
            }
        } else {
            for (const line of order.lines) {
                if (line._orig_discount_refund !== undefined) {
                    line.setDiscount(line._orig_discount_refund);
                    delete line._orig_discount_refund;
                }
            }
        }

        order.triggerRecomputeAllPrices();

        if (order.payment_ids.length === 1) {
            const pl = order.payment_ids[0];
            pl.setAmount(order.totalDue);
            this.numberBuffer.set(order.totalDue.toString());
        } else if (this.selectedPaymentLine) {
            this.selectedPaymentLine.setAmount(order.totalDue);
            this.numberBuffer.set(order.totalDue.toString());
        }
    },
});
