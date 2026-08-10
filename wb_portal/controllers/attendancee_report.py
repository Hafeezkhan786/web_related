# -*- coding: utf-8 -*-
from odoo import models


class EmployeeAttendanceData(models.Model):
    """Server action behind the "Print Attendance" button on hr.attendance."""
    _inherit = "hr.attendance"

    def click_button(self, ids=None):
        records = ids if ids else self
        c_data = {}
        for rec in records:
            c_data[rec.id] = {
                'emp': rec.employee_id.name,
                'checkin': rec.check_in,
                'checkout': rec.check_out,
                'workhours': rec.worked_hours,
            }
        data = {'c_data': c_data}
        return self.env.ref(
            'wb_portal.employee_attendance_portal'
        ).report_action(self, data=data)
