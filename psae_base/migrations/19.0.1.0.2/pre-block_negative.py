import logging

from odoo.upgrade.util.fields import move_field_to_module, rename_field
from odoo.upgrade.util.modules import force_install_module, merge_module, module_installed
from odoo.upgrade.util.pg import copy_column
from odoo.upgrade.util.records import force_noupdate, remove_view, rename_xmlid

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Block Negative Suite 19.0.1.0.2 pre-migration: starting (from version %s)", version)

    if version < "19.0.1.0.0":
        _logger.info("Migrating from v18 and below")
        _pre_migrate_v17_v18_clients(cr)
    if version == "19.0.1.0.0":
        _logger.info("Migrating from 19.0.1.0.0")
        _pre_migrate_v19_0_clients(cr)
    if version == "19.0.1.0.1":
        _logger.info("Migrating from 19.0.1.0.1")
        _pre_migrate_v19_1_clients(cr)


def _pre_migrate_v17_v18_clients(cr):
    if module_installed(cr, "psae_block_transfers"):
        remove_view(cr, "psae_block_transfers.product_category_form_view")
        remove_view(cr, "psae_block_transfers.product_template_form_view")
        rename_field(cr, "product.template", "allow_negative", "is_negative_transfer_allowed")
        merge_module(cr, "psae_block_transfers", "psae_block_negative_transfers")
    if module_installed(cr, "block_negative_pos"):
        remove_view(cr, "block_negative_pos.view_template_property_form_inherit_block_negative_pos")
        remove_view(cr, "block_negative_pos.inherited_view_employee_form")
        remove_view(cr, "block_negative_pos.res_config_settings_view_form")
        rename_field(cr, "product.template", "allow_negative_pos", "is_negative_pos_allowed")
        merge_module(cr, "block_negative_pos", "psae_block_negative_pos")
    if module_installed(cr, "block_negative_sale"):
        remove_view(cr, "block_negative_sale.view_template_property_form_inherit_block_negative_sale")
        remove_view(cr, "block_negative_sale.inherited_view_order_form")
        merge_module(cr, "block_negative_sale", "psae_block_negative_sale")

    _migrate_allow_negative_group(cr, "qty_block_base.group_allow_negative_sale")


def _pre_migrate_v19_0_clients(cr):
    # AHMNs — only had the transfers extension, no sale module
    remove_view(cr, "psae_block_transfers.product_category_form_view")
    remove_view(cr, "psae_block_transfers.product_template_form_view")
    # Make sure that the group has the noupdate flag set
    # Before migration to make it consistent with the V17, V18 clients
    force_noupdate(cr, "psae_base_qty_block.group_allow_negative_sale")
    _migrate_allow_negative_group(cr, "psae_base_qty_block.group_allow_negative_sale")

    # Renaming the field maps it correctly when the new module installs
    rename_field(cr, "product.template", "allow_negative", "is_negative_transfer_allowed")
    # Move the field before installing to avoid deletion conflicts
    move_field_to_module(cr, "product.template", "is_negative_transfer_allowed", "psae_block_transfers", "psae_block_negative_transfers")  # fmt:skip
    force_install_module(cr, "psae_block_negative_transfers", if_installed=["psae_block_transfers", "psae_base_qty_block"])  # fmt:skip


def _pre_migrate_v19_1_clients(cr):
    # Habib Trading — base views removed, base module no longer part of internal
    remove_view(cr, "psae_block_negative_base.product_category_form_view")
    remove_view(cr, "psae_block_negative_base.product_template_form_view")
    if module_installed(cr, "psae_block_negative_transfers"):
        copy_column(cr, "product_template", "allow_negative", "is_negative_transfer_allowed")
    if module_installed(cr, "psae_block_negative_pos"):
        copy_column(cr, "product_template", "allow_negative", "is_negative_pos_allowed")
    # move_field_to_module is a no-op if the field or module does not exist
    move_field_to_module(cr, "sale.order.line", "qty_in_progress", "psae_block_negative_base", "psae_block_negative_pos")  # fmt:skip
    # Make sure that the group has the noupdate flag set
    # Before migration to make it consistent with the V17, V18 clients
    force_noupdate(cr, "psae_block_negative_base.group_allow_negative_sale")
    _migrate_allow_negative_group(cr, "psae_block_negative_base.group_allow_negative_sale")


def _migrate_allow_negative_group(cr, old_xmlid):
    """Copy group comment, then rename the old shared group to whichever new module owns it."""
    copy_column(cr, "res_groups", "comment", "comment_copy")
    if module_installed(cr, "psae_block_negative_transfers") or module_installed(cr, "psae_block_transfers"):
        rename_xmlid(cr, old_xmlid, "psae_block_negative_transfers.group_allow_negative_transfers")
    elif module_installed(cr, "psae_block_negative_sale"):
        rename_xmlid(cr, old_xmlid, "psae_block_negative_sale.group_allow_negative_sale")
