# PSAE Block Negative Sales (Point of Sale)

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Internal Architecture](#internal-architecture)
- [Edge Cases Addressed](#edge-cases-addressed)
- [Dependencies](#dependencies)
- [Configuration and Setup](#configuration-and-setup)

---

## Overview

The **PSAE Block Negative Sales (Point of Sale)** module prevents cashiers from opening the payment screen when available stock is insufficient to cover the order. The check runs via RPC at the moment the cashier taps Pay, before the payment screen opens.

The block is enforced in the JS layer via a `PosStore.pay()` override. A single RPC call (`pos.config.check_quantity`) handles all stock validation server-side. The JS layer is responsible for building the payload and deciding which dialog to show based on the cashier's role.

This module is **standalone** — it does not depend on any other module in the block negative suite.

**Lines of Code:** 139 Python · 90 JS

---

## Key Features

- **Hard block at payment:** Stock check runs when the cashier taps Pay, before the payment screen opens. Cannot be bypassed by dismissing a dialog.
- **Serial/lot validation:** Lines with tracked products and missing lot/serial assignments are hard-blocked before the stock check runs. Managers are exempt so they can override when needed (e.g. lot created on the fly at delivery).
- **SO-aware delta check:** For lines linked to a Sale Order, only the quantity beyond the SO's already-reserved qty (`qty_in_progress`) is sent to `check_quantity` — preventing false blocks on legitimate SO settlements.
- **Role-based response:** Managers get a `ConfirmationDialog` and can choose to proceed (e.g. intentional oversell). Regular employees get an `AlertDialog` and are hard-blocked.
- **Per-product exception:** Products with `is_negative_pos_allowed = True` are excluded from the stock check entirely.
- **Configurable stock source:** `negative_qty_block_source` on `pos.config` controls whether the check uses the operation type's source location or the full warehouse assigned to the POS.

---

## Internal Architecture

**`product.template.is_negative_pos_allowed`** (Boolean)

Marks a product as exempt from all POS stock checks. Defaults to `False`. Visible to POS managers on the product form under **Negative Quantities Restriction**. Loaded into the POS session via `product.product._load_pos_data_fields`.

**`pos.config.negative_qty_block_source`** (Selection)

Controls the stock location used by `check_quantity`:

- `operation_type` *(default)* — checks the source location of the POS picking type.
- `warehouse` — checks the full warehouse assigned to the POS.

**`pos.config.check_quantity`** (RPC method)

Server-side enforcement point. Receives `[[product_id, lot_name|null, qty], ...]` and returns a translated error string listing insufficient products, or `""` if all quantities are available. Only storable products with `is_negative_pos_allowed = False` are evaluated. Lot/serial handling:

- **Lot-tracked:** checks `free_qty` for the specific lot. Lines with an unknown lot name are skipped — the lot may be created at delivery.
- **Serial-tracked:** each serial counts as qty 1 regardless of line quantity. Lines with no lot assigned are skipped.
- **Untracked:** checks total `free_qty` with no lot context.

**`sale.order.line.qty_in_progress`** (Float, stored, computed)

Quantity currently reserved by the SO's assigned outgoing moves but not yet delivered. Loaded into the POS session. The JS layer uses it to compute the true delta before sending lines to `check_quantity`, so already-reserved SO quantities are never double-counted.

**`PosStore.pay()`** (JS override)

Two checks run in sequence before `super.pay()`:

1. **Serial/lot validation** (non-managers only): If any line has a tracked product with no valid lot/serial, an `AlertDialog` is shown and payment is blocked.
2. **Stock quantity check**: Builds `[[product_id, lot_name|null, qty], ...]` from the current order lines — using `qty_in_progress` delta for SO-linked lines — and sends it to `check_quantity` via RPC. On error: manager sees `ConfirmationDialog`, employee sees `AlertDialog`. On RPC failure: falls through to `super.pay()` to avoid blocking the cashier.

---

## Edge Cases Addressed

**SO settlement without extra units**

When a cashier settles a Sale Order in POS without adding extra lines, the SO's delivery moves are still in state `assigned` — reserved stock is not yet reflected in `free_qty`. Without the `qty_in_progress` delta, the check would see artificially low available stock and falsely block the settlement. The delta computation ensures only genuinely new demand is checked.

**RPC failure**

If `check_quantity` raises an exception (e.g. network error, server error), the override falls through to `super.pay()` rather than blocking the cashier. Availability errors should never prevent legitimate sales due to infrastructure issues.

---

## Dependencies

- `psae_base`
- `pos_hr` — required for cashier role detection (`_role` on the cashier object).
- `pos_sale` — required for SO settlement and `qty_in_progress` on `sale.order.line`.

---

## Configuration and Setup

### Per-product

Navigate to **POS > Products**, open a product, and look for the **Negative Quantities Restriction** group (visible to POS managers only):

- **Allow Negative POS** — when enabled, the stock check is skipped for that product entirely.

### POS Config

Open **POS > Configuration > Point of Sale**, then under **Inventory Settings**:

- **Negative Qty Block Source**
  - `Operation Type` *(default)* — checks the source location of the POS picking type.
  - `Warehouse` — checks the full warehouse assigned to the POS.
