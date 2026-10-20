import { patch } from '@web/core/utils/patch';
import {
    ProductConfiguratorDialog,
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

patch(ProductConfiguratorDialog.prototype, {
    /**
     * Clamps the requested quantity to the effective maximum — the lower of
     * available stock (`free_qty`) and the website purchase cap
     * (`allowed_ecommerce_qty`) — before delegating to the parent.
     * Only applied in website frontend context (`isFrontend: true`).
     *
     * @override
     * @param {number} productTmplId - The id of the product template being updated.
     * @param {number} quantity - The requested new quantity.
     */
    async _setQuantity(productTmplId, quantity) {
        if (this.props.isFrontend) {
            const product = this._findProduct(productTmplId);
            const effectiveMax = product.allowed_ecommerce_qty || (product.free_qty ?? Infinity);
            quantity = Math.min(quantity, effectiveMax);
        }
        return super._setQuantity(productTmplId, quantity);
    },

    /**
     * Check whether the provided product quantity can be added to the cart,
     * using the stricter of available stock (`free_qty`) and the website
     * purchase cap (`allowed_ecommerce_qty`) as the effective maximum.
     * Falls back to the parent implementation outside of frontend context.
     *
     * @override
     * @param {Object} product - The product whose quantity is being checked.
     * @param {number} quantity - The quantity to check.
     * @return {boolean} - Whether the quantity is within the effective maximum.
     */
    _isQuantityAllowed(product, quantity) {
        if (!this.props.isFrontend) return super._isQuantityAllowed(product, quantity);
        return product.isQuantityAllowed(quantity);
    },
});
