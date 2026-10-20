import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import { registry } from "@web/core/registry";
import * as ProductScreenAddons from "./utils/product_screen_util_addons";

registry.category("web_tour.tours").add("disabled_neg_qty_tour", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Chrome.endTour(),
        ].flat(),
});
registry.category("web_tour.tours").add("enabled_neg_qty_tour", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
            Chrome.endTour(),
        ].flat(),
});
registry.category("web_tour.tours").add("successful_payment_tour", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
            Chrome.endTour(),
        ].flat(),
});
registry.category("web_tour.tours").add("unsuccessful_payment_tour", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_employee_unsuccessful_payment", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Employee B", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Dialog.confirm(),
            {
                timeout: 50000,
                content: "Still in product screen",
                trigger: ".product-screen",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_employee_successful_payment_confirm_negative_warning", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Employee B", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Dialog.confirm("Proceed"),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("lot_tracked_product_success", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(false),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("lot_tracked_product_fail", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.addOrderline("Whiteboard Pen", "2"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("serial_tracked_product_success", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.enterExistingLotNumber("serial1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.enterExistingLotNumber("serial2"),
            ProductScreen.clickPayButton(false),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("serial_tracked_product_fail", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.enterExistingLotNumber("serial1"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.enterExistingLotNumber("serial2"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.enterExistingLotNumber("serial3"),
            ProductScreen.clickPayButton(false),
            ProductScreenAddons.isErrorDialogShown("Available Stock Exceeded"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("block_negative_pos_settle_so_good", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            {
                timeout: 5000,
                content: "now in payment screen",
                trigger: ".pos-content .payment-screen",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("block_negative_pos_settle_extra_warning", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Employee B", { run: "click" }),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.clickPayButton(false),
            Dialog.is("Available Stock"),
            Dialog.confirm("Proceed"),
            {
                content: "Now in payment screen",
                trigger: ".pos-content .payment-screen",
                timeout: 10000,
            },
        ].flat(),
});

registry.category("web_tour.tours").add("block_negative_pos_settle_extra_block", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Employee B", { run: "click" }),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.clickPayButton(false),
            Dialog.is("Available Stock"),
            Dialog.confirm(),
            {
                content: "Still in product screen",
                trigger: ".product-screen",
            },
        ].flat(),
});
