import StockVariantMixin from '@website_sale_stock/js/variant_mixin';

const _originalOnChangeCombinationStock = StockVariantMixin._onChangeCombinationStock;

/**
 * On every combination change: refresh our custom UoM labels (core only updates
 * the DOM nodes it knows about, so they keep their server-rendered values) and
 * cap add-to-cart qty at `allowed_ecommerce_qty` on top of the stock max.
 *
 * Loads before `website_sale.js` (`before` directive in __manifest__.py): v19
 * still `Object.assign(WebsiteSale.prototype, VariantMixin)`s at eval time, so a
 * later patch never reaches the interaction prototype.
 *
 * @override
 */
StockVariantMixin._onChangeCombinationStock = async function (_ev, parent, combination) {
    if (combination && combination.allowed_ecommerce_qty) {
        combination.free_qty = combination.allowed_ecommerce_qty;
        combination.virtual_available = combination.allowed_ecommerce_qty;
        combination.qty_available = combination.allowed_ecommerce_qty;
    }

    // Core ends with an unguarded `…querySelector('div.availability_messages')
    // .append(…)`; ensure the container exists (where website_sale_stock puts
    // it, before #o_wsale_cta_wrapper) so core runs fully instead of throwing.
    if (!this.el.querySelector('div.availability_messages')) {
        const container = document.createElement('div');
        container.className = 'availability_messages';
        const cta = this.el.querySelector('#o_wsale_cta_wrapper');
        cta ? cta.before(container) : this.el.append(container);
    }
    await _originalOnChangeCombinationStock.apply(this, arguments);

    // Re-sync the custom UoM labels from the new payload; core leaves them untouched.
    for (const [wrapperSel, valueSel, value] of [
        ['.o_psae_uom_per_label', '.o_psae_uom_per_value', combination.uom_per_label],
        ['.o_psae_website_uom_label', '.o_psae_website_uom_label', combination.website_uom_label],
    ]) {
        const wrapper = parent.querySelector(wrapperSel);
        if (!wrapper) continue;
        parent.querySelector(valueSel).innerHTML = value || '';
        wrapper.classList.toggle('d-none', !value);
    }

    const uomLabel = (combination.uom_per_label || combination.website_uom_label || '').toLowerCase();
    const isBox = uomLabel.includes('box');
    const isStrip = uomLabel.includes('strip') && !isBox;

    const allowedQty = combination.allowed_ecommerce_qty;

    const addQtyInput = parent.querySelector('input[name="add_qty"]');
    if (!addQtyInput) return;

    if (allowedQty) {
        addQtyInput.max = allowedQty;
        addQtyInput.dataset.max = allowedQty;
    } else {
        addQtyInput.removeAttribute('max');
        delete addQtyInput.dataset.max;
    }

    const checkStripQtyWarning = () => {
        let warningEl = parent.querySelector('.o_strip_qty_warning');
        const currentQty = parseFloat(addQtyInput.value || 1);

        if (allowedQty && currentQty >= allowedQty) {
            if (currentQty > allowedQty) {
                addQtyInput.value = allowedQty;
            }
            if (!warningEl) {
                warningEl = document.createElement('div');
                warningEl.className = 'alert alert-warning o_strip_qty_warning mt-2 mb-2 p-2.5 rounded-3 shadow-sm border-warning d-flex align-items-center gap-2';
                const ctaWrapper = parent.querySelector('#o_wsale_cta_wrapper');
                ctaWrapper ? ctaWrapper.after(warningEl) : addQtyInput.after(warningEl);
            }
            let noticeTitle = 'Limit Notice:';
            let noticeText = `You cannot order more than ${allowedQty} per order.`;
            if (isBox) {
                noticeTitle = 'Box Limit Notice:';
                noticeText = `Aap ${allowedQty} box se ziyada order nahi kar saktay. (Maximum ${allowedQty} Boxes allowed per order)`;
            } else if (isStrip) {
                noticeTitle = 'Strip Limit Notice:';
                noticeText = `Aap ${allowedQty} strip se ziyada order nahi kar saktay. (Maximum ${allowedQty} Strips allowed per order)`;
            }
            warningEl.innerHTML = `
                <i class="fa fa-exclamation-triangle text-warning fs-5 flex-shrink-0"></i>
                <div class="small fw-semibold text-dark">
                    <strong>${noticeTitle}</strong> ${noticeText}
                </div>
            `;
            warningEl.classList.remove('d-none');
        } else {
            if (warningEl) {
                warningEl.classList.add('d-none');
            }
        }
    };

    if (allowedQty && parseFloat(addQtyInput.value) > allowedQty) {
        addQtyInput.value = allowedQty;
    }

    checkStripQtyWarning();

    if (!addQtyInput.dataset.stripListenerAttached) {
        addQtyInput.dataset.stripListenerAttached = 'true';
        ['input', 'change'].forEach(evt => {
            addQtyInput.addEventListener(evt, checkStripQtyWarning);
        });
    }
};
