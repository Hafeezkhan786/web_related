import { patch } from '@web/core/utils/patch';
import {
    ProductConfiguratorDialog,
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

/**
 * Hotfix for:
 *   OwlError: TypeError: product.isQuantityAllowed is not a function
 *       at _isQuantityAllowed (product_configurator_dialog.js)
 *
 * Root cause
 * ----------
 * `psae_medicine_custom_website_pos` overrides `_isQuantityAllowed()` to
 * delegate the stock/website-cap check to `product.isQuantityAllowed()`.
 * That method only exists on `ProductProduct` model instances (patched in
 * `psae_medicine_custom_website_pos/static/src/js/models/product_product.js`).
 * However, `_isQuantityAllowed()` is also called by the dialog's own
 * `isOutOfStock()` template helper with plain product records coming
 * straight from the RPC/configurator payload (not wrapped in the
 * `ProductProduct` class), which do not carry that method — hence the
 * crash and the resulting blank/broken configurator dialog.
 *
 * Fix
 * ---
 * Re-implement the check locally so it never assumes `isQuantityAllowed`
 * exists on `product`. If it *is* available (real `ProductProduct`
 * instance) we still use it; otherwise we fall back to computing the
 * effective max quantity (min of available stock and the website
 * ecommerce cap) directly from the plain record's fields.
 */
patch(ProductConfiguratorDialog.prototype, {
    _isQuantityAllowed(product, quantity) {
        if (!this.props.isFrontend) {
            return super._isQuantityAllowed(product, quantity);
        }

        if (product && typeof product.isQuantityAllowed === 'function') {
            return product.isQuantityAllowed(quantity);
        }

        const freeQty = product?.free_qty ?? Infinity;
        const ecommerceCap = product?.allowed_ecommerce_qty || Infinity;
        const effectiveMax = Math.min(freeQty, ecommerceCap);

        return quantity <= effectiveMax;
    },
});
