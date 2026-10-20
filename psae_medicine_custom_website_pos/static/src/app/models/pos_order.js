import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@web/core/currency";


patch(PosOrder.prototype, {
    /**
     * Returns the total amount due including any surcharge fees from payment methods.
     *
     * @return {number} - Sum of the base total due and the total surcharge.
     */
    get displayTotalDue() {
        return this.totalDue + this.totalSurcharge;
    },
    /**
     * Returns the total amount due, including surcharge, formatted as a currency
     * string in the order's currency.
     *
     * @return {string} - The formatted total due.
     */
    get formattedDisplayTotalDue() {
        return formatCurrency(this.displayTotalDue, this.currency.id);
    },
    /**
     * Calculates the total surcharge across all payment lines that belong to
     * a surcharge-enabled payment method.
     *
     * @return {number} - Total surcharge amount for the order.
     */
    get totalSurcharge() {
        return this.payment_ids
            .filter((pl) => pl.payment_method_id.has_surcharge)
            .reduce((sum, pl) => sum + (pl.surchargeAmount || 0), 0);
    },
    /**
     * Returns the total surcharge formatted as a currency string in the order's
     * currency.
     *
     * @return {string} - The formatted total surcharge.
     */
    get formattedTotalSurcharge() {
        return formatCurrency(this.totalSurcharge, this.currency.id);
    },
});
