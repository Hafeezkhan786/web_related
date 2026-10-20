from odoo.upgrade import util


def migrate(cr, version):
    if util.module_installed(cr, "warehouse_record_rules"):
        util.merge_module(cr, "warehouse_record_rules", "psae_warehouse_record_rules")
