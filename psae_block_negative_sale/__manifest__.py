{
    "name": "PSAE | Block Negative Sales",
    "version": "19.0.2.0.0",
    "category": "PSAE/Sales",
    "summary": "Hard block on Sale Order confirm and line add when stock is insufficient.",
    "description": """
        PSAE Block Negative Sales
        =======================================
        Prevents confirming a Sale Order or adding lines to a confirmed Sale Order
        when one or more storable lines would result in negative stock.

        Standalone — no other module in the block negative suite depends on this one.

        Key Behaviors:
        - Hard block: _action_launch_stock_rule on sale.order.line calls super() first
          so stock moves are created, then checks free_qty_today < qty_to_deliver via
          float_compare on any line where display_qty_widget is True. UserError rolls
          back the transaction. Fires on both initial confirm and confirmed-SO line adds.
        - Bypass group: Users in "Allow Negative Quantity on Sale" skip the check
          entirely.
        - No custom quantity logic: availability is evaluated using Odoo's standard
          display_qty_widget, free_qty_today, and qty_to_deliver fields — the same
          data that drives the red forecast chart icon.
    """,
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": ["psae_base", "sale_stock"],
    "data": ["security/res_groups.xml"],
}
