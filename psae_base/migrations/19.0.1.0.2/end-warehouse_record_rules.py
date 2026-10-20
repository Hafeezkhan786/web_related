import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Starting end-warehouse_record_rules migration")

    _logger.info("cleanup of old modules")
    util.remove_module(cr, "warehouse_record_rules")
    _logger.info("end-warehouse_record_rules migration complete")
