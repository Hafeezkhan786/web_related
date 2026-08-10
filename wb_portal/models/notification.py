# -*- coding: utf-8 -*-
"""In-portal notifications for the WB HR Employee Portal (Odoo 18).

A lightweight notification center: records are created for the affected user
(e.g. the leave approver when a request is submitted, the employee when a
request is approved/refused) and displayed in a bell dropdown on every portal
page. Notifications never contain sensitive data and are plain rows, so no
extra access rights are needed beyond the portal's own user checks.
"""
from odoo import _, api, fields, models


class WBPortalNotification(models.Model):
    _name = 'wb.notification'
    _description = 'HR Portal Notification'
    _order = 'create_date desc, id desc'

    user_id = fields.Many2one(
        'res.users', string='User', required=True, index=True,
        ondelete='cascade')
    title = fields.Char(string='Title', required=True, translate=True)
    body = fields.Text(string='Message', translate=True)
    notification_type = fields.Selection([
        ('leave', 'Time Off'),
        ('attendance', 'Attendance'),
        ('document', 'Document'),
        ('payslip', 'Payslip'),
        ('system', 'System'),
    ], string='Type', default='system', index=True)
    read = fields.Boolean(string='Read', default=False, index=True)
    url = fields.Char(string='Target URL')
    related_model = fields.Char(string='Related Model')
    related_id = fields.Integer(string='Related Record')

    _sql_constraints = [
        ('check_user', 'CHECK(user_id IS NOT NULL)',
         'A notification must belong to a user.'),
    ]

    @api.model
    def _notify_user(self, user, title, body, notification_type='system',
                     url=False, related_model=False, related_id=False):
        """Create a notification for a single user (safe no-op when missing)."""
        if not user:
            return False
        return self.sudo().create({
            'user_id': user.id,
            'title': title,
            'body': body,
            'notification_type': notification_type,
            'url': url or False,
            'related_model': related_model or False,
            'related_id': related_id or False,
        })

    @api.model
    def _unread_count(self, user_id):
        return self.search_count([
            ('user_id', '=', user_id),
            ('read', '=', False),
        ])


class HrLeaveNotification(models.Model):
    """Hook the time off lifecycle to create portal notifications."""
    _inherit = 'hr.leave'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_leave_approvers(self):
        """Users responsible for approving these leaves (portal context)."""
        users = self.env['res.users'].sudo()
        group_user = self.env.ref(
            'hr_holidays.group_hr_holidays_user', raise_if_not_found=False)
        for leave in self:
            manager = leave.employee_id.leave_manager_id if leave.employee_id else False
            if manager:
                users |= manager
            elif group_user:
                users |= self.env['res.users'].sudo().search([
                    ('groups_id', 'in', group_user.id),
                    ('share', '=', False),
                ])
        return users

    def _notify_leave_approval(self):
        """Notify the employee about the current approval state."""
        notify = self.env['wb.notification'].sudo()
        for leave in self:
            user = leave.employee_id.user_id
            if not user:
                continue
            reference = leave.sequence or leave.display_name
            if leave.state == 'validate':
                notify._notify_user(
                    user, _('Time off approved'),
                    _('Your time off request %s was approved.', reference),
                    'leave', '/leaveview/', 'hr.leave', leave.id)
            elif leave.state == 'validate1':
                notify._notify_user(
                    user, _('Time off - awaiting final approval'),
                    _('Your time off request %s has passed the first approval.',
                      reference),
                    'leave', '/leaveview/', 'hr.leave', leave.id)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        notify = self.env['wb.notification'].sudo()
        for leave in leaves:
            # 1) Notify the approver(s) inside the portal
            title = _('New time off request')
            body = _('A new time off request was submitted by %s.',
                     leave.employee_id.name)
            for user in leave._get_leave_approvers():
                notify._notify_user(
                    user, title, body, 'leave',
                    '/leavesapproval/', 'hr.leave', leave.id)

            # 2) Send the notification email (leave manager only, queued)
            manager = leave.employee_id.leave_manager_id if leave.employee_id else False
            if manager and manager.email:
                template = self.env.ref(
                    'wb_portal.email_template_for_leave_request',
                    raise_if_not_found=False)
                if template:
                    try:
                        template.with_context(
                            lang=manager.lang or self.env.lang or 'en_US'
                        ).send_mail(leave.id, force_send=False)
                    except Exception:
                        # Never block leave creation because of an email issue
                        pass
        return leaves

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state=check_state)
        # For two-step (validation_type='both') leaves this is only the FIRST
        # approval (state 'validate1'); for single-step leaves super() already
        # called action_validate(), which sends the "approved" notification.
        self.filtered(lambda l: l.state == 'validate1')._notify_leave_approval()
        return res

    def action_validate(self, check_state=True):
        res = super().action_validate(check_state=check_state)
        self._notify_leave_approval()
        return res

    def action_refuse(self):
        res = super().action_refuse()
        notify = self.env['wb.notification'].sudo()
        for leave in self:
            user = leave.employee_id.user_id
            if not user:
                continue
            notify._notify_user(
                user, _('Time off refused'),
                _('Your time off request %s was refused.',
                  leave.sequence or leave.display_name),
                'leave', '/leaveview/', 'hr.leave', leave.id)
        return res
