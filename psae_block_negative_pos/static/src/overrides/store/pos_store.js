import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Override of PosStore.pay() to enforce stock availability before opening the payment screen.
     *
     * Two checks run in sequence:
     *
     * 1. Lot/serial validation (non-managers only)
     *    Odoo's standard pay() already warns when lot/serial numbers are missing, but it only
     *    shows a confirmation — the cashier can dismiss it and proceed. This override turns that
     *    into a hard block for regular employees. Managers are exempt so they can override when
     *    needed (e.g. lot created on the fly at delivery).
     *
     * 2. Stock quantity check
     *    Builds a flat list of [product_id, lot_name|null, qty] tuples and sends them to
     *    pos.config.check_quantity via RPC. For lines linked to a Sale Order, only the delta
     *    beyond the SO's already-reserved qty (qty_in_progress) is checked — the SO's delivery
     *    moves hold that stock and will release it when the POS order is validated.
     *
     *    - Manager: ConfirmationDialog — can choose to proceed (e.g. intentional oversell).
     *    - Employee: AlertDialog — hard block, must contact manager.
     *    - RPC failure: falls through to super.pay() to avoid blocking the cashier on errors.
     */
    async pay() {
        const currentOrder = this.getOrder();
        const cashier = this.getCashier();
        if (
            cashier._role !== "manager" &&
            currentOrder.lines.some(
                (line) => !line.getProduct().is_negative_pos_allowed && line.getProduct().tracking !== "none" && !line.hasValidProductLot()
            ) &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        ) {
            return this.dialog.add(AlertDialog, {
                title: _t("Some Serial/Lot Numbers are missing"),
                body: _t("You must assign serial/lot numbers to all products before proceeding."),
            });
        }
        const productLotQtyMap = new Map();
        for (const {
            product_id: { id, tracking },
            qty: rawQty,
            pack_lot_ids,
            sale_order_line_id,
        } of currentOrder.lines) {
            const qty = Math.max(0, rawQty - (sale_order_line_id?.qty_in_progress ?? 0));
            if (qty === 0) continue;
            if (pack_lot_ids.length === 0) {
                const k = `${id}:`;
                productLotQtyMap.set(k, [id, null, (productLotQtyMap.get(k)?.[2] ?? 0) + qty]);
            }
            for (const { lot_name } of pack_lot_ids) {
                const k = `${id}:${lot_name}`;
                const delta = tracking === "serial" ? 1 : qty;
                productLotQtyMap.set(k, [id, lot_name, (productLotQtyMap.get(k)?.[2] ?? 0) + delta]);
            }
        }
        const orderLines = [...productLotQtyMap.values()];

        if (!cashier || !this.config || !orderLines.length) return super.pay();

        let negative_quants_error;
        try {
            negative_quants_error = await this.data.call("pos.config", "check_quantity", [orderLines, this.config.id]);
        } catch {
            return super.pay();
        }

        if (!negative_quants_error) return super.pay();

        if (cashier._role === "manager") {
            return this.dialog.add(ConfirmationDialog, {
                title: _t("Available Stock Exceeded"),
                body: _t(negative_quants_error + "\n\nAre you sure you want to proceed?"),
                confirm: () => super.pay(),
                cancel: () => {},
                confirmLabel: _t("Proceed"),
            });
        }
        return this.dialog.add(AlertDialog, {
            title: _t("Available Stock Exceeded"),
            body: _t(negative_quants_error + "\n\nPlease adjust the quantities or contact your manager."),
        });
    },
});
