import logging

from odoo.upgrade import util
from odoo.upgrade.util.modules import module_installed, remove_module
from odoo.upgrade.util.orm import env
from odoo.upgrade.util.report import add_to_migration_reports, announce_migration_report

_logger = logging.getLogger(__name__)

_OLD_MODULES = (
    # V17, V18
    "qty_block_base",
    "block_negative_pos",
    "block_negative_sale",
    "psae_block_negative_pos_sale",
    "psae_block_transfers",
    # V19.0.1.0.0
    "psae_base_qty_block",
    # V19.0.1.0.1
    "psae_block_negative_base",
)


def migrate(cr, version):
    _logger.info("Block Negative Suite 19.0.1.0.2 end-migration: starting (from version %s)", version)

    # Clients coming from V18, V17
    if version < "19.0.1.0.0":
        _logger.info("Migrating groups from v18 and below")
        _migrate_group(
            cr,
            transfer_group_xml_id="psae_block_negative_transfers.group_allow_negative_transfers",
            sale_group_xml_id="psae_block_negative_sale.group_allow_negative_sale",
        )

    # Clients Like Habib Trading
    if version == "19.0.1.0.1":
        _logger.info("Migrating groups from 19.0.1.0.1")
        _migrate_group(
            cr,
            transfer_group_xml_id="psae_block_negative_transfers.group_allow_negative_transfers",
            sale_group_xml_id="psae_block_negative_sale.group_allow_negative_sale",
        )

    # To Retain the old behaviour of blocking on transfers
    if module_installed(cr, "psae_block_negative_transfers"):
        env(cr)["stock.picking.type"].search([("code", "=", "outgoing")]).write({"is_block_negative": True})

    # We remove old modules regardless of what was executed in the pre and end migrations
    for module in _OLD_MODULES:
        remove_module(cr, module)

    _add_migration_report(cr)


def _migrate_group(cr, transfer_group_xml_id, sale_group_xml_id):
    # Run in end-migrate so upgraded modules have their new groups available.
    # transfer_group is already handled in pre-migrate.
    transfer_group = env(cr)["res.groups"].browse(util.ref(cr, transfer_group_xml_id) or 0).exists()
    sale_group = env(cr)["res.groups"].browse(util.ref(cr, sale_group_xml_id) or 0).exists()
    if source := (transfer_group or sale_group):
        cr.execute(
            "UPDATE res_groups SET comment = comment_copy WHERE id = %s AND comment_copy IS NOT NULL", [source.id]
        )
    util.remove_column(cr, "res_groups", "comment_copy")
    new_data = {"name": "Allow Negative Quantity on Sale"}
    sale_group.write(transfer_group.copy_data(new_data)[0] if transfer_group else new_data)
    transfer_group.write({"name": "Allow Negative Quantity on Move Operations"})


def _add_migration_report(cr):
    has_transfers = module_installed(cr, "psae_block_negative_transfers")
    has_sale = module_installed(cr, "psae_block_negative_sale")
    has_pos = module_installed(cr, "psae_block_negative_pos")

    installed = []
    if has_transfers:
        installed.append(
            "<li>"
            "<b>Block Negative Transfers</b> (<code>psae_block_negative_transfers</code>)<br/>"
            "Controls negative stock on delivery operations per operation type via the new "
            "<b>Block Negative Quantity</b> (<code>is_block_negative</code>) field on <code>stock.picking.type</code>.<br/>"
            "Users with the <b>Allow Negative Quantity on Move Operations</b> group can bypass this "
            "per product using the <b>Allow Negative Transfers</b> (<code>is_negative_transfer_allowed</code>) field."
            "</li>"
        )
    if has_sale:
        installed.append(
            "<li>"
            "<b>Block Negative Sale</b> (<code>psae_block_negative_sale</code>)<br/>"
            "Blocks sale order confirmation when stock is insufficient.<br/>"
            "Users with the <b>Allow Negative Quantity on Sale</b> group can bypass this check."
            "</li>"
        )
    if has_pos:
        installed.append(
            "<li>"
            "<b>Block Negative PoS</b> (<code>psae_block_negative_pos</code>)<br/>"
            "Blocks POS payment when stock is insufficient.<br/>"
            "Per-product override available via the <b>Allow Negative PoS</b> (<code>is_negative_pos_allowed</code>) field.<br/>"
            "If login with employee PIN is enabled, all users at the <b>Advanced</b> access level can bypass the block."
            "</li>"
        )

    if not installed:
        return

    modules_list = "".join(installed)
    delivery_note = (
        "<p>Delivery operation types have been set to "
        "<b>Block Negative Quantity = True</b> to retain the previous blocking behaviour.</p>"
        if has_transfers
        else ""
    )
    add_to_migration_reports(
        message=f"""
            <details open>
                <summary><b>Block Negative Stock — Suite Restructured</b></summary>
                <p>
                    The block negative stock suite has been split into three fully independent modules.
                    Each module can be installed or uninstalled without affecting the others.
                    The following modules are currently active on your database:
                </p>
                <ul>{modules_list}</ul>
                <p>All existing group memberships and product settings have been automatically migrated.</p>
                {delivery_note}
            </details>
        """,
        category="PSAE",
        format="html",
    )
    announce_migration_report(cr)
