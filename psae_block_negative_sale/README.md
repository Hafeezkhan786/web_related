# PSAE Module: Block Negative Sales (Sale Order)

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Internal Architecture](#internal-architecture)
- [Dependencies](#dependencies)
- [Behavior](#behavior)

---

## Overview

The **PSAE Block Negative Sales (Sale Order)** module hard-blocks Sale Order confirmation and line additions when one or more storable order lines have insufficient stock.

The block is enforced at the ORM level via `_action_launch_stock_rule` on `sale.order.line` — the same method Odoo calls when procurement rules are launched, both on initial confirm and when new lines are added to a confirmed order.

Availability is driven entirely by Odoo's own standard fields on `sale.order.line` (`free_qty_today`, `qty_to_deliver`) — no custom quantity logic is introduced. Comparisons use `float_compare` with the line's UOM rounding.

This module is **standalone** — it does not depend on any other module in the block negative suite.

**Lines of Code:** 22

---

## Key Features

- **Hard block on confirm:** `UserError` is raised if any storable line has `free_qty_today < qty_to_deliver` at the moment procurement rules fire.
- **Hard block on line addition:** Adding a line to an already-confirmed SO goes through the same path and is equally blocked.
- **Bypass group:** Users in the **Allow Negative Quantity on Sale** group skip the check entirely and can confirm or add lines regardless of stock.
- **Zero custom qty logic:** Availability is evaluated using Odoo's existing `free_qty_today` and `qty_to_deliver` fields — the same data that drives the red forecast chart icon on order lines.

---

## Internal Architecture

**`sale.order.line._action_launch_stock_rule`** (override)

Called by Odoo when procurement rules are about to be launched — on both `action_confirm` and confirmed-SO line writes. The override:

1. Skips the check if the current user has `group_allow_negative_sale`.
2. Calls `super()` first so stock moves are created and `free_qty_today` is correctly populated from `move.forecast_availability`.
3. Checks via `any()` whether any line with `display_qty_widget = True` has `free_qty_today < qty_to_deliver`.
4. Raises a generic `UserError` if so — rolling back the transaction and all created moves.

`display_qty_widget` is the single guard — it is `True` only for storable lines with pending delivery and active moves, which means service products, fully delivered lines, and lines with no moves are all excluded automatically.

---

## Dependencies

- `psae_base`
- `sale_stock`

---

## Behavior

### Stock sufficient (`free_qty_today >= qty_to_deliver` on all storable lines)
- Confirm proceeds normally.
- Adding lines to a confirmed SO proceeds normally.

### Stock insufficient (at least one storable line is short)

- **Regular user:** `UserError` — "Oops! Not enough stock. Check the forecast view on the order lines."
- **Bypass user** (`group_allow_negative_sale`): Check is skipped entirely — confirm and line additions proceed without restriction.
