import { patch } from '@web/core/utils/patch';
import { ProductProduct } from '@sale/js/models/product_product';

patch(ProductProduct.prototype, {
    /**
     * Extends the stock-aware setup to also store `allowed_ecommerce_qty`
     * received from the configurator data payload.
     *
     * @override
     * @param {number} allowed_ecommerce_qty - Maximum purchasable quantity enforced on the website.
     * @param args - Remaining arguments forwarded to the parent setup.
     */
    setup({ allowed_ecommerce_qty, ...args }) {
        super.setup(args);
        this.allowed_ecommerce_qty = allowed_ecommerce_qty;
    },

    /**
     * Check whether the provided quantity can be added to the cart, using the
     * stricter of available stock (`free_qty`) and the website purchase cap
     * (`allowed_ecommerce_qty`) as the effective maximum.
     *
     * @override
     * @param {number} quantity - The quantity to check.
     * @return {boolean} - Whether the quantity is within the effective maximum.
     */
    isQuantityAllowed(quantity) {
        const effectiveMax = this.allowed_ecommerce_qty || (this.free_qty ?? Infinity);
        return quantity <= effectiveMax;
    },
});
