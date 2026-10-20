/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.NaheedSinglePageCheckout = publicWidget.Widget.extend({
    selector: ".o_naheed_checkout_page",
    events: {
        "change input[name='delivery_type']": "_onShippingMethodChange",
        "change input[name='payment_method_code']": "_onPaymentMethodChange",
        "input #naheed_order_notes": "_onOrderNotesInput",
        "change #naheed_order_notes": "_onOrderNotesChange",
        "change #naheed_country_id": "_onCountryChange",
        "change #naheed_state_id": "_onStateChange",
        "change .form-group-naheed input, .form-group-naheed select": "_onAddressFieldChange",
        "click .js_btn_complete_order": "_onCompleteOrderClick",
        "input #naheed_phone, #naheed_mobile": "_onPhoneInput",
        "change #naheed_billing_same_as_delivery": "_onBillingSameAsDeliveryToggle",
        "change #naheed_billing_country_id": "_onBillingCountryChange",
        "input #naheed_billing_phone": "_onPhoneInput",
        "input input, change select": "_onClearCustomValidity",
    },

    // ═══════════════════════════════════════════════════════════
    // BILLING SAME AS DELIVERY
    // ═══════════════════════════════════════════════════════════
    _onBillingSameAsDeliveryToggle(ev) {
        const $checkbox = $(ev.currentTarget);
        const $wrapper = $("#naheed_billing_address_wrapper");
        const isChecked = $checkbox.is(":checked");

        if (isChecked) {
            $wrapper.slideUp(200);
            $wrapper.find('input[type="text"], input[type="tel"], input[type="email"]').val('');
            $wrapper.find('select#naheed_billing_state_id').val('');
            $wrapper.find('input, select').removeAttr('required');
        } else {
            this._copyDeliveryToBilling();
            $wrapper.slideDown(200);
            $(
                "#naheed_billing_first_name, #naheed_billing_last_name, " +
                "#naheed_billing_phone, #naheed_billing_street, " +
                "#naheed_billing_street2, #naheed_billing_city, " +
                "#naheed_billing_country_id, #naheed_billing_state_id, " +
                "#naheed_billing_email"
            ).attr('required', 'required');
        }
    },

    _copyDeliveryToBilling() {
        const firstName = ($("#naheed_first_name").val() || "").trim();
        const lastName = ($("#naheed_last_name").val() || "").trim();
        $("#naheed_billing_first_name").val(firstName);
        $("#naheed_billing_last_name").val(lastName);

        const phone = ($("#naheed_phone").val() || "").trim();
        const email = ($("#naheed_email").val() || "").trim();
        $("#naheed_billing_phone").val(phone);
        $("#naheed_billing_email").val(email);

        const street = ($("#naheed_address").val() || "").trim();
        const street2 = ($("#naheed_street2").val() || "").trim();
        const city = ($("#naheed_city").val() || "").trim();
        const zip = ($("#naheed_zip").val() || "").trim();
        $("#naheed_billing_street").val(street);
        $("#naheed_billing_street2").val(street2);
        $("#naheed_billing_city").val(city);
        $("#naheed_billing_zip").val(zip);

        const countryId = $("#naheed_country_id").val() || "";
        const $billingCountry = $("#naheed_billing_country_id");
        $billingCountry.val(countryId);

        const stateId = $("#naheed_state_id").val() || "";
        if (countryId) {
            this._loadBillingStatesForCountry(countryId).then(() => {
                if (stateId) {
                    $("#naheed_billing_state_id").val(stateId);
                }
            });
        }
    },

    // ═══════════════════════════════════════════════════════════
    // ADDRESS FIELD CHANGE — triggers delivery + payment re-render
    // ═══════════════════════════════════════════════════════════
    async _onAddressFieldChange(ev) {
        const firstName = ($("#naheed_first_name").val() || "").trim();
        const lastName = ($("#naheed_last_name").val() || "").trim();
        const name = [firstName, lastName].filter(Boolean).join(" ");
        const phone = $("#naheed_phone").val() || "";
        const mobile = $("#naheed_mobile").val() || "";
        const street = $("#naheed_address").val() || "";
        const street2 = $("#naheed_street2").val() || "";
        const city = $("#naheed_city").val() || "";
        const stateId = $("#naheed_state_id").val() || "";
        const countryId = $("#naheed_country_id").val() || "";
        const email = $("#naheed_email").val() || "";
        const zip = $("#naheed_zip").val() || "";

        this._syncDeliveryToBillingIfNeeded();

        try {
            const data = await this._callRpc("/shop/single_checkout/update_address", {
                name: name,
                phone: phone,
                mobile: mobile,
                street: street,
                street2: street2,
                city: city,
                state_id: stateId,
                country_id: countryId,
                email: email,
                zip: zip,
            });

            if (data && data.success) {
                if (data.delivery_methods !== undefined) {
                    this._renderDeliveryMethods(data.delivery_methods, data.carrier_id);
                }
                if (data.payment_options !== undefined) {
                    this._renderPaymentMethods(data.payment_options);
                }
                if (!data.carrier_id) {
                    $(".js_summary_shipping_amount").text("Rs. 0.00");
                    $(".js_summary_carrier_name").text("Select shipping method");
                } else if (data.amount_delivery_formatted) {
                    $(".js_summary_shipping_amount").text(data.amount_delivery_formatted);
                }
                if (data.amount_total_formatted) {
                    $(".js_summary_total_amount").text(data.amount_total_formatted);
                }
            }
        } catch (err) {
            console.error("Address auto-update error:", err);
        }
    },

    _syncDeliveryToBillingIfNeeded() {
        const $checkbox = $("#naheed_billing_same_as_delivery");
        const $wrapper = $("#naheed_billing_address_wrapper");

        if ($checkbox.is(":checked")) return;
        if (!$wrapper.is(":visible")) return;
        if ($wrapper.data('manually-edited')) return;

        this._copyDeliveryToBilling();
    },

    // ═══════════════════════════════════════════════════════════
    // START
    // ═══════════════════════════════════════════════════════════
    start() {
        this._super.apply(this, arguments);
        this._updateCharCounter();

        const $countrySelect = $("#naheed_country_id");
        if ($countrySelect.val()) {
            this._loadStatesForCountry($countrySelect.val());
        }

        this._setupBillingEditTracking();
    },

    _setupBillingEditTracking() {
        const $wrapper = $("#naheed_billing_address_wrapper");
        const billingFields = [
            "#naheed_billing_first_name",
            "#naheed_billing_last_name",
            "#naheed_billing_phone",
            "#naheed_billing_email",
            "#naheed_billing_street",
            "#naheed_billing_street2",
            "#naheed_billing_city",
            "#naheed_billing_zip",
            "#naheed_billing_state_id",
            "#naheed_billing_country_id",
        ];

        billingFields.forEach(selector => {
            $(selector).on('input change', () => {
                $wrapper.data('manually-edited', true);
            });
        });

        $("#naheed_billing_same_as_delivery").on('change', () => {
            if (!$("#naheed_billing_same_as_delivery").is(":checked")) {
                $wrapper.data('manually-edited', false);
            }
        });
    },

    // ═══════════════════════════════════════════════════════════
    // BILLING COUNTRY CHANGE
    // ═══════════════════════════════════════════════════════════
    async _onBillingCountryChange(ev) {
        const countryId = $(ev.currentTarget).val();
        await this._loadBillingStatesForCountry(countryId);
    },

    async _loadBillingStatesForCountry(countryId) {
        const $stateSelect = $("#naheed_billing_state_id");

        if (!countryId) {
            $stateSelect.html(
                '<option value="">Please select a region, state or province</option>'
            );
            return;
        }

        try {
            const data = await this._callRpc("/shop/single_checkout/get_states", {
                country_id: countryId,
            });

            if (data && data.states) {
                let html = '<option value="">Please select a region, state or province</option>';
                data.states.forEach(state => {
                    html += `<option value="${state.id}">${this._escapeHtml(state.name)}</option>`;
                });
                $stateSelect.html(html);
            }
        } catch (err) {
            console.error("Error loading billing states:", err);
        }
    },

    // ═══════════════════════════════════════════════════════════
    // PHONE INPUT
    // ═══════════════════════════════════════════════════════════
    _onPhoneInput(ev) {
        const $input = $(ev.currentTarget);
        let val = $input.val();
        val = val.replace(/[^\d+]/g, '');
        if (val.indexOf('+') > 0) {
            val = val.replace(/\+/g, '');
        }
        if (val.startsWith('+')) {
            val = val.substring(0, 13);
        } else if (val.startsWith('0')) {
            val = val.substring(0, 11);
        } else {
            val = val.substring(0, 11);
        }
        $input.val(val);
    },

    // ═══════════════════════════════════════════════════════════
    // RPC HELPER
    // ═══════════════════════════════════════════════════════════
    async _callRpc(route, params) {
        try {
            const response = await fetch(route, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: params || {},
                    id: Math.floor(Math.random() * 1000000),
                }),
            });
            const json = await response.json();
            if (json.error) {
                console.error("RPC error for route", route, json.error);
                return { error: json.error };
            }
            return json.result;
        } catch (err) {
            console.error("RPC fetch exception for route", route, err);
            throw err;
        }
    },

    // ═══════════════════════════════════════════════════════════
    // COUNTRY / STATE CHANGE
    // ═══════════════════════════════════════════════════════════
    async _onCountryChange(ev) {
        const countryId = $(ev.currentTarget).val();
        await this._loadStatesForCountry(countryId);
        await this._onAddressFieldChange(ev);
    },

    async _loadStatesForCountry(countryId) {
        const $stateSelect = $("#naheed_state_id");
        if (!countryId) {
            $stateSelect.html(
                '<option value="">Please select a region, state or province</option>'
            );
            return;
        }
        try {
            const data = await this._callRpc("/shop/single_checkout/get_states", {
                country_id: countryId,
            });
            if (data && data.states) {
                let html = '<option value="">Please select a region, state or province</option>';
                data.states.forEach(state => {
                    html += `<option value="${state.id}">${this._escapeHtml(state.name)}</option>`;
                });
                $stateSelect.html(html);
            }
        } catch (err) {
            console.error("Error loading states:", err);
        }
    },

    async _onStateChange(ev) {
        await this._onAddressFieldChange(ev);
    },

    // ═══════════════════════════════════════════════════════════
    // SHIPPING METHOD CHANGE — re-renders payment options
    // ═══════════════════════════════════════════════════════════
    async _onShippingMethodChange(ev) {
        const $radio = $(ev.currentTarget);
        const $list = $radio.closest(".shipping-methods-list");
        $list.find(".naheed-option-card").removeClass("active");
        $radio.closest(".naheed-option-card").addClass("active");

        const carrierId = $radio.val();
        if (!carrierId) return;

        try {
            const data = await this._callRpc("/shop/single_checkout/update_delivery", {
                carrier_id: carrierId,
            });

            if (data && data.success) {
                // Update order summary
                $(".js_summary_shipping_amount").text(data.amount_delivery_formatted);
                $(".js_summary_total_amount").text(data.amount_total_formatted);
                $(".js_summary_carrier_name").text(data.carrier_name);

                // ✅ Re-render filtered payment options
                if (data.payment_options !== undefined) {
                    console.log(
                        "🔄 Re-rendering payment methods after carrier change:",
                        data.payment_options.map(o => o.name)
                    );
                    this._renderPaymentMethods(data.payment_options);
                }
            } else if (data && data.error) {
                console.error("Delivery update error:", data.error);
            }
        } catch (err) {
            console.error("Error updating delivery method:", err);
        }
    },

    // ═══════════════════════════════════════════════════════════
    // PAYMENT METHOD CHANGE
    // ═══════════════════════════════════════════════════════════
    _onPaymentMethodChange(ev) {
        const $radio = $(ev.currentTarget);
        const $list = $radio.closest(".payment-methods-list");
        $list.find(".naheed-option-card").removeClass("active");
        $radio.closest(".naheed-option-card").addClass("active");

        const selectedMethodCode = $radio.val();
        $list.find(".naheed-payment-info-box").hide();
        $list
            .find(`.naheed-payment-info-box[data-for-method='${selectedMethodCode}']`)
            .show();
    },

    // ═══════════════════════════════════════════════════════════
    // ORDER NOTES
    // ═══════════════════════════════════════════════════════════
    _onOrderNotesInput(ev) {
        this._updateCharCounter();
    },

    async _onOrderNotesChange(ev) {
        const noteText = $(ev.currentTarget).val();
        try {
            await this._callRpc("/shop/single_checkout/update_notes", { note: noteText });
        } catch (err) {
            console.error("Error saving order notes:", err);
        }
    },

    _updateCharCounter() {
        const $textarea = $("#naheed_order_notes");
        if (!$textarea.length) return;
        const maxLen = 300;
        const currentLen = $textarea.val().length;
        const remaining = maxLen - currentLen;
        $("#naheed_notes_char_counter").text(remaining >= 0 ? remaining : 0);
    },

    // ═══════════════════════════════════════════════════════════
    // RENDER DELIVERY METHODS
    // ═══════════════════════════════════════════════════════════
    _renderDeliveryMethods(deliveryMethods, selectedCarrierId) {
        const $container = $(".shipping-methods-list");
        if (!$container.length) return;

        if (!deliveryMethods || !deliveryMethods.length) {
            $container.html(
                '<div class="text-muted p-2">No shipping methods available for the selected region.</div>'
            );
            return;
        }

        let html = '';
        deliveryMethods.forEach((dm) => {
            const isChecked = selectedCarrierId && dm.id === selectedCarrierId;
            const activeClass = isChecked ? 'active' : '';
            html += `
                <label class="naheed-option-card ${activeClass}">
                    <div class="option-left">
                        <input type="radio" name="delivery_type" value="${dm.id}"
                               ${isChecked ? 'checked="checked"' : ''} required="required"/>
                        <span class="option-title">${this._escapeHtml(dm.name)}</span>
                    </div>
                    <span class="option-price">${this._escapeHtml(dm.price_formatted)}</span>
                </label>
            `;
        });
        $container.html(html);
    },

    // ═══════════════════════════════════════════════════════════
    // RENDER PAYMENT METHODS
    // ═══════════════════════════════════════════════════════════
    _renderPaymentMethods(paymentOptions) {
        const $container = $(".payment-methods-list");
        if (!$container.length) return;

        console.log(
            "💳 _renderPaymentMethods called with:",
            paymentOptions ? paymentOptions.map(o => o.name) : "empty/null"
        );

        if (!paymentOptions || !paymentOptions.length) {
            $container.html(
                '<div class="text-muted p-2">No payment methods available for the selected region.</div>'
            );
            return;
        }

        let html = '';
        paymentOptions.forEach((opt) => {
            const iconHtml = opt.badge_icon
                ? `<i class="${this._escapeHtml(opt.badge_icon)}"></i>` : '';
            const radioValue = this._escapeHtml(opt.code || String(opt.id));
            const providerId = opt.provider_id || '';
            const paymentMethodId = opt.payment_method_id || '';
            const providerCode = opt.provider_code || '';

            html += `
                <label class="naheed-option-card">
                    <div class="option-left">
                        <input type="radio" name="payment_method_code"
                               value="${radioValue}"
                               data-provider-id="${providerId}"
                               data-payment-method-id="${paymentMethodId}"
                               data-provider-code="${this._escapeHtml(providerCode)}"
                               required="required"/>
                        <span class="option-title">${this._escapeHtml(opt.name)}</span>
                    </div>
                    <span class="${this._escapeHtml(opt.badge_class || 'option-badge')}">
                        ${iconHtml} ${this._escapeHtml(opt.badge_text || opt.name)}
                    </span>
                </label>
            `;
            if (opt.pending_msg) {
                html += `
                    <div class="naheed-payment-info-box"
                         data-for-method="${radioValue}"
                         style="display: none;">
                        <div class="d-flex align-items-start gap-2 p-3 mt-2 mb-3 rounded"
                             style="background-color: #fff9e6; border-left: 4px solid #f0ad4e;">
                            <i class="fa fa-info-circle text-warning mt-1"></i>
                            <div class="flex-grow-1 small text-dark">${opt.pending_msg}</div>
                        </div>
                    </div>
                `;
            }
        });
        $container.html(html);
    },

    // ═══════════════════════════════════════════════════════════
    // HTML ESCAPE
    // ═══════════════════════════════════════════════════════════
    _escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    _onClearCustomValidity(ev) {
        if (ev.currentTarget && typeof ev.currentTarget.setCustomValidity === 'function') {
            ev.currentTarget.setCustomValidity("");
        }
    },

    // ═══════════════════════════════════════════════════════════
    // COMPLETE ORDER CLICK
    // ═══════════════════════════════════════════════════════════
    _onCompleteOrderClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const form = document.getElementById("naheed_single_checkout_form");
        if (!form) return;

        // 1. Check required shipping fields (all except WhatsApp & Zip)
        const requiredShippingSelectors = [
            "#naheed_phone",
            "#naheed_first_name",
            "#naheed_last_name",
            "#naheed_city",
            "#naheed_address",
            "#naheed_street2",
            "#naheed_country_id",
            "#naheed_state_id",
            "#naheed_email",
        ];

        for (const selector of requiredShippingSelectors) {
            const input = document.querySelector(selector);
            if (input) {
                if (!input.value || !input.value.trim()) {
                    input.setCustomValidity("Please fill out this field.");
                    input.reportValidity();
                    return;
                } else {
                    input.setCustomValidity("");
                }
            }
        }

        // 2. If separate billing address is used, check billing required fields
        const isBillingSeparate = !$("#naheed_billing_same_as_delivery").is(":checked");
        if (isBillingSeparate) {
            const requiredBillingSelectors = [
                "#naheed_billing_first_name",
                "#naheed_billing_last_name",
                "#naheed_billing_phone",
                "#naheed_billing_street",
                "#naheed_billing_street2",
                "#naheed_billing_city",
                "#naheed_billing_country_id",
                "#naheed_billing_state_id",
                "#naheed_billing_email",
            ];
            for (const selector of requiredBillingSelectors) {
                const input = document.querySelector(selector);
                if (input) {
                    if (!input.value || !input.value.trim()) {
                        input.setCustomValidity("Please fill out this field.");
                        input.reportValidity();
                        return;
                    } else {
                        input.setCustomValidity("");
                    }
                }
            }
        }

        // 3. Native HTML5 form validation (email format, phone regex pattern, etc.)
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        // 4. Shipping method check
        const $selectedCarrier = $("input[name='delivery_type']:checked");
        if (!$selectedCarrier.length) {
            const firstCarrierRadio = document.querySelector("input[name='delivery_type']");
            if (firstCarrierRadio) {
                firstCarrierRadio.reportValidity();
            } else {
                alert("Please select a shipping method.");
            }
            return;
        }

        // 5. Payment method check
        const $selectedPayment = $("input[name='payment_method_code']:checked");
        if (!$selectedPayment.length) {
            const firstPaymentRadio = document.querySelector("input[name='payment_method_code']");
            if (firstPaymentRadio) {
                firstPaymentRadio.reportValidity();
            } else {
                alert("Please select a payment method.");
            }
            return;
        }

        const providerId = $selectedPayment.attr('data-provider-id');
        const paymentMethodId = $selectedPayment.attr('data-payment-method-id');

        if (!providerId) {
            alert("Selected payment method is invalid. Please choose another.");
            return;
        }

        $("#checkout_provider_id").val(providerId || "");
        $("#checkout_payment_method_id").val(paymentMethodId || "");

        const $btn = $(".js_btn_complete_order");
        $btn.prop('disabled', true).text('Processing Order...');

        $("#naheed_single_checkout_form").submit();
    },
});

export default publicWidget.registry.NaheedSinglePageCheckout;