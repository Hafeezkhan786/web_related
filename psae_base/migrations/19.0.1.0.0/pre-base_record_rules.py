from odoo.upgrade import util


def migrate(cr, version):
    if util.module_installed(cr, "base_record_rules"):
        util.merge_module(cr, "base_record_rules", "psae_base_record_rules")
