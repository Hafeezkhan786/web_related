import { patch } from '@web/core/utils/patch';
import { ComboConfiguratorDialog } from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

// Declares `allowed_ecommerce_qty` as a valid optional prop so OWL does not
// raise an "unknown key" validation error when the configurator data payload
// includes it alongside the stock-provided `free_qty`.
patch(ComboConfiguratorDialog.props, {
    allowed_ecommerce_qty: { type: Number, optional: true },
});

patch(ComboConfiguratorDialog.prototype, {
    /**
     * Clamps the requested quantity to the effective maximum — the lower of
     * the sub-item stock limit and the website purchase cap
     * (`allowed_ecommerce_qty`) — before delegating to the parent.
     *
     * @override
     * @param {number} quantity - The requested new quantity.
     */
    async setQuantity(quantity) {
        const cap = this.props.allowed_ecommerce_qty;
        if (cap && quantity > cap) {
            quantity = cap;
        }
        return super.setQuantity(quantity);
    },

    /**
     * Check whether the provided combo quantity can be added to the cart,
     * also enforcing the website purchase cap (`allowed_ecommerce_qty`) on
     * the main combo product in addition to each sub-item's stock check.
     *
     * @override
     * @param {number} quantity - The quantity to check.
     * @return {boolean} - Whether the quantity is within all effective limits.
     */
    isComboQuantityAllowed(quantity) {
        const cap = this.props.allowed_ecommerce_qty;
        return super.isComboQuantityAllowed(quantity) && (!cap || cap >= quantity);
    },
});
