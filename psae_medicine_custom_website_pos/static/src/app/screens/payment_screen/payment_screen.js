import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@web/core/currency";

patch(PaymentScreen.prototype, {
    /**
     * Returns the surcharge amount for a given payment method formatted as a
     * currency string prefixed with "+", e.g. "+5.00 SAR".
     *
     * @param {Object} paymentMethod - The payment method whose surcharge is being calculated.
     * @return {string} - Formatted surcharge amount string.
     */
    getFormattedSurchargeAmount(paymentMethod) {
        const order = this.currentOrder;
        return `+${formatCurrency(
            order.getDefaultAmountDueToPayIn(paymentMethod) * paymentMethod.surcharge_percent || 0, order.currency.id
        )}`;
    },
    /**
     * Extends order validation to inject surcharge lines before finalising the
     * order. For each payment method with a surcharge, the surcharge amount is
     * added to the payment line and a corresponding product line is appended to
     * the order. Refund orders bypass this logic and delegate directly to the
     * parent.
     *
     * @override
     * @param {boolean} [isForceValidate=false] - Whether to force validation regardless of warnings.
     * @return {Promise<void>}
     */
    async validateOrder(isForceValidate = false) {
        if (this.currentOrder.isRefund) {
            return super.validateOrder(...arguments)
        }
        const paymentLines = this.paymentLines.filter(
            (line) =>
                line.payment_method_id.has_surcharge &&
            line.payment_method_id.surcharge_product_id
        );
        for (const [_, lines] of Object.entries(Object.groupBy(
            paymentLines,
            (line) => line.payment_method_id.surcharge_product_id.id
        ))) {
            const product = lines[0].payment_method_id.surcharge_product_id;
            const price = lines.reduce((a, {surchargeAmount}) => a + surchargeAmount, 0);
            lines.forEach((line) => line.setAmount(line.amount + line.surchargeAmount));
            await this.pos.addLineToCurrentOrder(
                {
                    product_id: product,
                    product_tmpl_id: product.product_tmpl_id,
                    price_unit: price,
                },
                {},
                false
            );
        };
        return super.validateOrder(...arguments);
    },
});
