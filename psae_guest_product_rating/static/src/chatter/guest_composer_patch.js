import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { useState } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.guestState = useState({
            guestName: "",
            guestEmail: "",
            isSubmitting: false,
            submittedSuccess: false,
            errorMessage: "",
        });
    },

    get isGuestUser() {
        return session.is_public;
    },

    get canProcessMessage() {
        if (this.isGuestUser) {
            return true;
        }
        return super.canProcessMessage;
    },

    get isSendButtonDisabled() {
        if (this.isGuestUser && (this.env.displayRating || this.props.composer?.targetThread?.model === "product.template")) {
            return this.guestState.isSubmitting;
        }
        return super.isSendButtonDisabled;
    },

    async sendMessage() {
        const chatterEl = document.querySelector(".o_portal_chatter");
        const resModel = this.props.composer?.targetThread?.model || chatterEl?.getAttribute("data-res_model");
        const resId = this.props.composer?.targetThread?.id || parseInt(chatterEl?.getAttribute("data-res_id"));

        if (this.isGuestUser && (this.env.displayRating || resModel === "product.template")) {
            if (this.guestState.isSubmitting) {
                return;
            }
            this.guestState.isSubmitting = true;
            this.guestState.errorMessage = "";

            const textValue = this.props.composer?.composerText || this.props.composer?.text || "";

            try {
                const result = await rpc("/website/guest_rating/post", {
                    res_model: resModel || "product.template",
                    res_id: resId,
                    rating_value: this.portalState?.ratingValue || 5,
                    guest_name: this.guestState.guestName,
                    guest_email: this.guestState.guestEmail,
                    body: textValue,
                });

                if (result && result.success) {
                    this.guestState.submittedSuccess = true;
                    if (this.props.composer?.clear) {
                        this.props.composer.clear();
                    }
                    window.location.reload();
                } else {
                    this.guestState.errorMessage = result?.error || "Error submitting review.";
                }
            } catch (e) {
                this.guestState.errorMessage = "Failed to submit rating. Please try again.";
            } finally {
                this.guestState.isSubmitting = false;
            }
            return;
        }
        return super.sendMessage(...arguments);
    }
});
