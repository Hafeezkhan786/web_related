# -*- coding: utf-8 -*-
from odoo import models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Attendance report'
