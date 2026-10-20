import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { HeaderNoteButton } from "@psae_medicine_custom_website_pos/app/screens/product_screen/control_buttons/header_note_button/header_note_button";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        HeaderNoteButton,
    },
});
