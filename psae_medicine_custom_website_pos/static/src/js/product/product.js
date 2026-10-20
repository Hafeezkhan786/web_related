import { patch } from '@web/core/utils/patch';
import { Product } from '@sale/js/product/product';

// Declares `allowed_ecommerce_qty` as a valid optional prop so OWL does not
// raise an "unknown key" validation error when the configurator data payload
// includes it alongside the stock-provided `free_qty`.
patch(Product.props, {
    allowed_ecommerce_qty: { type: Number, optional: true },
});
