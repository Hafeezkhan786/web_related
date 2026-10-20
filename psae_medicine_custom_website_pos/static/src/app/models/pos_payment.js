import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { formatCurrency } from "@web/core/currency";

patch(PosPayment.prototype, {
    /**
     * Extends the base payment setup to calculate the initial surcharge amount
     * based on the payment method's surcharge percentage.
     *
     * @override
     * @param {Object} vals - Raw payment values from the server or session.
     */
    setup(vals) {
        super.setup(...arguments);
        this.setSurchargeAmount(this.amount);
    },
    /**
     * Extends the base amount setter to recalculate the surcharge whenever
     * the payment amount changes.
     *
     * @override
     * @param {number} value - The new payment amount.
     */
    setAmount(value) {
        super.setAmount(...arguments);
        this.setSurchargeAmount(value);
    },
    /**
     * Calculates and stores the surcharge amount for this payment line based on
     * the payment method's surcharge percentage. Sets surcharge to 0 if the
     * method has no surcharge or the amount is not positive.
     *
     * @param {number} value - The payment amount to base the surcharge calculation on.
     */
    setSurchargeAmount(value) {
        const pm = this.payment_method_id;
        const amountToPay = parseFloat(value) || 0;
        this.surchargeAmount = pm.has_surcharge && pm.surcharge_percent > 0 && amountToPay > 0 ? amountToPay * pm.surcharge_percent : 0;
    },
    /**
     * Returns the line's surcharge breakdown for display, formatted in the
     * order's currency: the surcharge added on top and the resulting total.
     * Each value is a currency string ready for <PriceFormatter>.
     *
     * @return {{surcharge: string, total: string}} - Formatted surcharge and total.
     */
    get surchargeBreakdown() {
        const currencyId = this.pos_order_id.currency.id;
        return {
            surcharge: formatCurrency(this.surchargeAmount, currencyId),
            total: formatCurrency(this.getAmount() + this.surchargeAmount, currencyId),
        };
    },
});
