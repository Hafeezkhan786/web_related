/** @odoo-module */

import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class HeaderNoteButton extends Component {
    static template = "psae_medicine_custom_website_pos.HeaderNoteButton";

    /**
     * Initialises the POS session reference and the dialog service used to
     * open the header note input popup.
     */
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    /**
     * Opens a text input popup to let the cashier set or update the header note
     * on the current order. Does nothing if no active order exists.
     */
    click() {
        const order = this.pos.getOrder();
        if (!order) return;
        this.dialog.add(TextInputPopup, {
            title: _t("Add Header Note"),
            startingValue: order.header_note || "",
            getPayload: (headerNote) => {order.header_note = headerNote;},
        });
    }
}
