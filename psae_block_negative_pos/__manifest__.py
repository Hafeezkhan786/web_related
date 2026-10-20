{
    "name": "PSAE | Block Negative Sales (Point of Sale)",
    "version": "19.0.2.0.0",
    "category": "PSAE/POS",
    "summary": "Hard block at POS payment when stock is insufficient, with role-based override for managers.",
    "description": """
        PSAE Block Negative Sales (Point of Sale)
        ==========================================
        Prevents cashiers from opening the payment screen when available stock is
        insufficient to cover the order. The check runs via RPC at the moment the
        cashier taps Pay, before the payment screen opens.

        Standalone — no other module in the block negative suite depends on this one.

        Key Behaviors:
        - is_negative_pos_allowed: Boolean on product.template. Products with this flag
          set are excluded from the stock check entirely.
        - Serial/lot hard block: Lines with tracked products and missing lot/serial
          assignments are blocked before the stock check runs. Managers are exempt.
        - SO-aware delta check: For lines linked to a Sale Order, only the quantity
          beyond the SO's already-reserved qty (qty_in_progress) is sent to
          check_quantity — preventing false blocks on legitimate SO settlements.
        - pos.config.check_quantity (RPC): Receives [[product_id, lot_name|null, qty], ...]
          and returns an error string or "" if all quantities are available.
        - Role-based response: Managers receive a ConfirmationDialog and can choose to
          proceed. Regular employees receive an AlertDialog and are hard-blocked.
        - Configurable stock source: negative_qty_block_source on pos.config controls
          whether the check uses the operation type's source location or the full
          warehouse assigned to the POS.
    """,
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": ["psae_base", "pos_hr", "pos_sale"],
    "data": ["views/pos_config.xml", "views/product_template_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "psae_block_negative_pos/static/src/**/*",
        ],
        "web.assets_tests": ["psae_block_negative_pos/static/tests/pos/tours/**/*"],
        "point_of_sale.assets_debug": [
            ("include", "point_of_sale.base_tests"),
            "psae_block_negative_pos/static/tests/pos/tours/**/*",
        ],
    },
}
