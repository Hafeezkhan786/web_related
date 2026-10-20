from itertools import groupby

from odoo import _, api, fields, models
from odoo.tools import float_compare


class PosConfig(models.Model):
    _inherit = "pos.config"

    negative_qty_block_source = fields.Selection(
        [("warehouse", "Warehouse"), ("operation_type", "Operation Type")], default="operation_type", required=True,  # fmt: skip
    )

    @api.model
    def check_quantity(self, order_lines, config_id):
        """
        RPC entry point called by the POS JS layer before opening the payment screen.

        Checks whether available stock covers the quantities in the order. Only storable
        products with ``is_negative_pos_allowed=False`` are evaluated — consumables and
        explicitly allowed products are skipped.

        Lot/serial handling:
        - Lot-tracked: checks free_qty for the specific lot. Lines with an unknown lot name
          (not found in the DB) are skipped — the lot may be created at delivery.
        - Serial-tracked: each serial counts as qty 1 regardless of the line quantity.
          Lines with no lot assigned are skipped (caught upstream by the JS serial block).
        - Untracked: checks total free_qty with no lot context.

        Stock source depends on ``negative_qty_block_source``:
        - ``operation_type``: checks the source location of the POS picking type.
        - ``warehouse``: checks the full warehouse assigned to the POS.

        :param order_lines: ``[[product_id: int, lot_name: str | None, qty: float], ...]``
        :param config_id: ID of the active ``pos.config`` record.
        :return: Translated error message string listing insufficient products, or ``""`` if all clear.
        """
        pos_config = self.env["pos.config"].browse(config_id)
        is_wh = pos_config.negative_qty_block_source == "warehouse"
        wh_id = pos_config.warehouse_id if is_wh else self.env["stock.warehouse"]
        loc_id = self.env["stock.location"] if is_wh else pos_config.picking_type_id.default_location_src_id

        product_ids = {product_id for product_id, _lot, _meta in order_lines}
        lot_names = {lot_name for _prod, lot_name, _meta in order_lines if lot_name}

        # POS returns lot_names, not actual lot_ids, using names to get actual records
        lot_map = {
            (product.id, name): lot
            for product, name, lot in self.env["stock.lot"].sudo()._read_group(
                [("name", "in", lot_names), ("product_id", "in", product_ids), ("product_id.is_negative_pos_allowed", "=", False)],
                ["product_id", "name"],
                ["id:recordset"],
            )
        } if lot_names else {}  # fmt:skip

        eligible = {p.id: p for p in self.env["product.product"].browse(product_ids) if p.is_storable and not p.is_negative_pos_allowed}  # fmt:skip

        insufficient = []
        for product_id, lot_name, qty in order_lines:
            if not (product := eligible.get(product_id)):
                continue
            lot = lot_map.get((product_id, lot_name), self.env["stock.lot"])
            if (lot_name and not lot) or (not lot_name and product.tracking != "none"):
                continue
            free_qty = product.with_context(warehouse_id=wh_id.id, location_id=loc_id.id, lot_id=lot.id).free_qty
            if float_compare(free_qty, qty, precision_rounding=product.uom_id.rounding) < 0:
                insufficient.append({"product_id": product, "lot_id": lot, "free_qty": free_qty, "ordered_qty": qty})

        if not insufficient:
            return ""
        parts = [_("Not enough available quantity for the following products:")]
        for product, items in groupby(insufficient, lambda r: r["product_id"]):
            parts.append(_("   • %s", product.display_name))
            for item in items:
                segments = [_("Lot/SN: %s", item["lot_id"].name)] if item.get("lot_id") else []
                segments.append(_("Additional Qty: %.2f", item["ordered_qty"] - item["free_qty"]))
                parts.append(_("\t%s", " | ".join(segments)))
        return "\n".join(parts)
