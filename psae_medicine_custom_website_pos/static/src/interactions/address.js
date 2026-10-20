import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { CustomerAddress } from "@portal/interactions/address";

const PHONE_RULES = {
    "pakistan": {
        message: "For Pakistan: Number must be +92... (13 digits) or 03... (11 digits).",
        validator: (num) => /^[0-9+]+$/.test(num) && (
            (num.startsWith("+92") && num.length === 13) ||
            (num.startsWith("03") && num.length === 11)
        ),
    },
    "united arab emirates": {
        message: "For UAE: Number must start with +971 and be 13 digits long.",
        validator: (num) => /^[0-9+]+$/.test(num) && (
            (num.startsWith("+971") && num.length === 13) ||
            (num.length === 9 && !num.includes("+"))
        ),
    },
};

patch(CustomerAddress.prototype, {
    /**
     * Extends setup to bind phone and mobile validation on change.
     *
     * @override
     */
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            "input[name='phone']": { "t-on-change": this._validatePhoneNumber.bind(this) },
            "input[name='custom_mobile']": { "t-on-change": this._validatePhoneNumber.bind(this) },
        });
    },

    /**
     * Overrides required-field logic to force email and zip as never required,
     * always require state_id, and pass all other fields through unchanged.
     *
     * @override
     * @param {string} name - Field name.
     * @param {boolean} required - Whether the field is natively required.
     */
    _markRequired(name, required) {
        super._markRequired(name, !["email", "zip"].includes(name) && (name === "state_id" || required));
    },

    /**
     * Runs phone and mobile validation before delegating to the parent save logic.
     *
     * @override
     */
    async saveAddress(...args) {
        this._validatePhoneNumber({ currentTarget: this.addressForm.phone });
        this._validatePhoneNumber({ currentTarget: this.addressForm.custom_mobile });
        return super.saveAddress(...args);
    },

    /**
     * Validates the phone number against country-specific rules defined in
     * `PHONE_RULES`. Marks the input invalid with a descriptive message when
     * the number does not match the expected format.
     *
     * @param {Event} param0 - Change event; destructured to `currentTarget` (the phone or mobile input).
     */
    _validatePhoneNumber({ currentTarget: input }) {
        const val = input.value.replace(/\s+/g, "");
        input.setCustomValidity("");
        input.classList.remove("is-invalid");
        if (!val) return;
        const countrySelect = this.addressForm.querySelector("select[name='country_id']");
        if (!countrySelect) return;
        const countryName = countrySelect.selectedOptions[0]?.text.toLowerCase();
        const rule = PHONE_RULES[countryName];
        if (rule && !rule.validator(val)) {
            input.classList.add("is-invalid");
            input.setCustomValidity(rule.message);
            input.reportValidity();
        }
    },
});
