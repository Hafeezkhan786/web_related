# -*- coding: utf-8 -*-
"""Employee self-service portal controllers (Odoo 18).

Includes portal check-in / check-out with optional geolocation validation,
per-user theme preference, payslips, time off and documents.
"""
import calendar
import math
import os
import urllib.parse
from datetime import date, datetime, timedelta

from odoo import _, fields as odoo_fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

from odoo.addons.portal.controllers.portal import CustomerPortal

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = ('.pdf', '.docx', '.pptx', '.jpg', '.jpeg', '.png')
ALLOWED_THEMES = ('default', 'ocean', 'emerald', 'sunset', 'midnight')


class WBEmployeePortal(CustomerPortal, http.Controller):
    """Modern employee portal built on the Odoo 18 portal framework."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _employee(self):
        """Current user's employee record (sudo'd for portal rendering)."""
        employee = request.env.user.employee_id.sudo()
        if not employee:
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', request.env.uid)], limit=1)
        return employee

    def _local_dt(self, value):
        """Convert a naive/UTC datetime to the user's timezone (or False)."""
        if not value:
            return False
        try:
            return odoo_fields.Datetime.context_timestamp(
                request.env.user, odoo_fields.Datetime.to_datetime(value))
        except Exception:
            return value

    def _parse_dates(self, start, end, default_start=None, default_end=None):
        """Parse two date strings (or fall back to sensible defaults)."""
        try:
            start_date = datetime.strptime(start, DF).date() if start else (default_start or date.today().replace(day=1))
        except (ValueError, TypeError):
            start_date = default_start or date.today().replace(day=1)
        try:
            end_date = datetime.strptime(end, DF).date() if end else (default_end or date.today())
        except (ValueError, TypeError):
            end_date = default_end or date.today()
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        return start_date, end_date

    def _base_values(self, page_name, title, crumb):
        """Shared rendering context for every portal page."""
        notif_env = request.env['wb.notification'].sudo()
        notifications = notif_env.search(
            [('user_id', '=', request.env.uid)], limit=12)
        notif_icons = {
            'leave': 'fa-plane',
            'attendance': 'fa-clock-o',
            'document': 'fa-file-o',
            'payslip': 'fa-file-text-o',
            'system': 'fa-info-circle',
        }
        wb_notifications = [{
            'id': n.id,
            'title': n.title,
            'body': n.body or '',
            'type': n.notification_type,
            'icon': notif_icons.get(n.notification_type, 'fa-info-circle'),
            'read': n.read,
            'url': n.url or '#',
            'time': self._relative_time(n.create_date),
        } for n in notifications]
        return {
            'page_name': page_name,
            'title': title,
            'wb_crumb': crumb,
            'emp': self._employee(),
            'no_breadcrumbs': True,
            'wb_theme_preset': request.session.get('wb_theme_preset', 'default'),
            'wb_notifications': wb_notifications,
            'wb_unread_count': notif_env._unread_count(request.env.uid),
        }

    def _relative_time(self, value):
        """Human friendly, translatable relative time for notifications."""
        if not value:
            return ''
        try:
            dt = odoo_fields.Datetime.to_datetime(value)
            seconds = (odoo_fields.Datetime.now() - dt).total_seconds()
        except Exception:
            return value
        if seconds < 60:
            return _('just now')
        minutes = int(seconds // 60)
        if minutes < 60:
            return _('%s minutes ago') % minutes
        hours = int(minutes // 60)
        if hours < 24:
            return _('%s hours ago') % hours
        days = int(hours // 24)
        if days < 7:
            return _('%s days ago') % days
        return dt.strftime('%d-%m-%Y')

    @http.route('/wb/notifications/read', type='json', auth='user', website=True,
                methods=['POST'])
    def wb_notification_read(self, notification_id=None, **kw):
        """Mark one (or all) notifications as read for the current user."""
        domain = [('user_id', '=', request.env.uid)]
        if notification_id:
            try:
                domain.append(('id', '=', int(notification_id)))
            except (TypeError, ValueError):
                domain.append(('id', '=', -1))
        request.env['wb.notification'].sudo().search(domain).write({'read': True})
        return {
            'ok': True,
            'unread': request.env['wb.notification'].sudo()._unread_count(
                request.env.uid),
        }

    def _unit_label(self, request_unit):
        if request_unit == 'hour':
            return _('hours')
        if request_unit == 'half_day':
            return _('half days')
        return _('days')

    def _is_leave_manager(self):
        return request.env.user.has_group('hr_holidays.group_hr_holidays_user') or bool(
            request.env['hr.employee'].sudo().search_count(
                [('leave_manager_id', '=', request.env.uid)]))

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        """Great-circle distance in kilometers between two GPS points."""
        earth_radius_km = 6371.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return earth_radius_km * 2 * math.asin(math.sqrt(a))

    # ------------------------------------------------------------------
    # Attendance (portal check-in / check-out)
    # ------------------------------------------------------------------
    def _attendance_context(self, employee):
        """Data needed by the check-in/out widget on any portal page."""
        last = employee.last_attendance_id.sudo()
        locations = request.env['hr.work.location'].sudo().search(
            [('active', '=', True)], order='name')
        loc_data = [{
            'id': loc.id,
            'name': loc.name,
            'geo_configured': loc.geo_configured,
            'geo_enforced': loc.geo_enforced,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'radius': loc.geo_radius,
        } for loc in locations]
        default_loc = employee.work_location_id
        geo_message = False
        if default_loc and default_loc.geo_configured:
            geo_message = _('Location check enabled: %s (allowed radius %.1f km)') % (
                default_loc.name, default_loc.geo_radius or 0.5)
        return {
            'att_state': employee.attendance_state,
            'last_attendance': last,
            'att_since': self._local_dt(last.check_in) if last else False,
            'att_until': self._local_dt(last.check_out) if last else False,
            'work_locations': loc_data,
            'default_location_id': default_loc.id if default_loc else (loc_data[0]['id'] if loc_data else False),
            'default_location_name': default_loc.name if default_loc else False,
            'geo_message': geo_message,
        }

    @http.route('/attendance/checkin/', type='json', auth='user', website=True,
                methods=['POST'])
    def portal_check_in_out(self, latitude=None, longitude=None,
                            work_location_id=None, **kw):
        """Check in / check out the current employee, with optional
        geolocation validation against the configured work location."""
        employee = self._employee()
        if not employee:
            return {'error': _('No employee profile is linked to your user account. '
                               'Please contact your HR administrator.')}

        try:
            lat = float(latitude) if latitude not in (None, '', False) else False
            lng = float(longitude) if longitude not in (None, '', False) else False
        except (TypeError, ValueError):
            lat = lng = False

        work_location = False
        if work_location_id:
            try:
                work_location = request.env['hr.work.location'].sudo().browse(
                    int(work_location_id)).exists()
            except (TypeError, ValueError):
                work_location = False
        if not work_location:
            work_location = employee.work_location_id

        distance = 0.0
        verified = False
        if work_location and work_location.geo_configured:
            if not lat or not lng:
                if work_location.geo_enforced:
                    return {'error': _(
                        'Location access is required to check in/out at %s. '
                        'Please allow location access in your browser and try again.',
                        work_location.name)}
            else:
                distance = self._haversine(
                    lat, lng, work_location.latitude, work_location.longitude)
                radius = work_location.geo_radius or 0.5
                if distance > radius:
                    return {'error': _(
                        'You are %(distance).1f km away from %(name)s. The allowed '
                        'radius is %(radius).1f km.',
                        distance=distance, name=work_location.name, radius=radius)}
                verified = True

        geo_information = {
            'latitude': lat or False,
            'longitude': lng or False,
            'ip_address': request.httprequest.remote_addr or False,
            'browser': request.httprequest.user_agent.browser
                       if request.httprequest.user_agent else False,
            'mode': 'portal',
        }
        try:
            attendance = employee.sudo()._attendance_action_change(geo_information)
        except (AccessError, UserError, ValidationError) as exc:
            return {'error': str(exc)}

        if attendance:
            attendance.write({
                'work_location_id': work_location.id if work_location else False,
                'geo_verified': verified,
            })

        state = 'in' if attendance.check_in and not attendance.check_out else 'out'
        if state == 'in':
            message = _('Checked in at %s.') % (
                work_location.name if work_location else _('work'))
        else:
            message = _('Checked out. Have a nice day!')
        return {
            'state': state,
            'message': message,
            'verified': verified,
            'distance_km': round(distance, 2) if verified else False,
            'attendance_id': attendance.id,
        }

    # ------------------------------------------------------------------
    # Theme preference (per user, stored in the session)
    # ------------------------------------------------------------------
    @http.route('/wb/theme/set', type='json', auth='user', website=True,
                methods=['POST'])
    def wb_theme_set(self, preset='default', **kw):
        preset = preset if preset in ALLOWED_THEMES else 'default'
        if preset == 'default':
            request.session.pop('wb_theme_preset', None)
        else:
            request.session['wb_theme_preset'] = preset
        return {'ok': True, 'preset': preset}

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @http.route('/home/', website=True, auth='user')
    def empoyeedata(self, **kw):
        employee = self._employee()
        if not employee:
            return request.render(
                'wb_portal.employee_not_linked_template',
                self._base_values('wb_home', _('Dashboard'), _('Dashboard')))

        today = date.today()
        start_date = today.replace(day=1)
        end_date = today

        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date + timedelta(days=1)),
        ], order='check_in')

        total_days = (end_date - start_date).days + 1
        bus_days = sum(
            1 for i in range(total_days)
            if (start_date + timedelta(days=i)).weekday() < 5)
        off_days = total_days - bus_days
        present_days = len(attendances)
        absent_days = max(bus_days - present_days, 0)
        worked_hours = sum(attendances.mapped('worked_hours'))

        # Leave balances - only types the employee can actually use
        leave_types = request.env['hr.leave.type'].sudo().search([
            '|',
            ('requires_allocation', '=', 'no'),
            ('has_valid_allocation', '=', True),
        ], order='sequence, name')

        balances = []
        for lt in leave_types:
            opening = lt.max_leaves or 0
            availed = lt.leaves_taken or 0
            balance = max(lt.virtual_remaining_leaves or 0, 0)
            pct = min(int((availed / opening * 100) if opening else 0), 100)
            balances.append({
                'name': lt.name,
                'opening': opening,
                'availed': availed,
                'balance': balance,
                'unit': self._unit_label(lt.request_unit),
                'pct': pct,
            })

        leaves = request.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee.id)])
        vals = self._base_values(
            'wb_home', _('Dashboard'),
            '%s - [%s]' % (employee.name, employee.barcode or '—'))
        vals.update(self._attendance_context(employee))
        vals.update({
            'present_days': present_days,
            'absent_days': absent_days,
            'off_days': off_days,
            'worked_hours': worked_hours,
            'balances': balances,
            'pending': len(leaves.filtered(lambda l: l.state == 'confirm')),
            'approved': len(leaves.filtered(lambda l: l.state == 'validate')),
            'refused': len(leaves.filtered(lambda l: l.state == 'refuse')),
            'month_name': calendar.month_name[start_date.month],
            'year': start_date.year,
        })
        return request.render('wb_portal.employee_form_view', vals)

    # ------------------------------------------------------------------
    # Attendance pages
    # ------------------------------------------------------------------
    @http.route('/attendance/', website=True, auth='user', type='http')
    def employeeattendata(self, **post):
        employee = self._employee()
        today = date.today()
        start_date, end_date = self._parse_dates(
            post.get('start_date'), post.get('end_date'),
            default_start=today.replace(day=1), default_end=today)

        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date + timedelta(days=1)),
        ], order='check_in')

        attendance_rows = []
        att_by_day = {}
        for att in attendances:
            local_in = self._local_dt(att.check_in)
            local_out = self._local_dt(att.check_out)
            if local_in:
                att_by_day.setdefault(local_in.date(), []).append(att)
            attendance_rows.append({
                'employee': att.employee_id.name,
                'department': att.department_id.name,
                'check_in': local_in,
                'check_out': local_out,
                'hours': att.worked_hours,
                'location': att.work_location_id.name or '',
                'geo_verified': att.geo_verified,
            })

        # Mini month calendar for the selected month
        month_start = start_date.replace(day=1)
        num_days = calendar.monthrange(month_start.year, month_start.month)[1]
        calendar_days = []
        for day_num in range(1, num_days + 1):
            day = month_start.replace(day=day_num)
            day_atts = att_by_day.get(day, [])
            calendar_days.append({
                'day': day_num,
                'is_weekend': day.weekday() >= 5,
                'is_today': day == today,
                'present': bool(day_atts),
                'hours': sum(a.worked_hours for a in day_atts),
            })

        vals = self._base_values('wb_attendance', _('My Attendance'), _('Attendance'))
        vals.update(self._attendance_context(employee))
        vals.update({
            'attendance_rows': attendance_rows,
            'total_hours': sum(attendances.mapped('worked_hours')),
            'calendar_days': calendar_days,
            'first_weekday': month_start.weekday(),
            'month_name': calendar.month_name[month_start.month],
            'year': month_start.year,
            'start_date': start_date,
            'end_date': end_date,
        })
        return request.render('wb_portal.my_attendance', vals)

    @http.route('/attendance/func/', website=True, auth='user', type='http')
    def func_call(self, **kw):
        """Download the attendance PDF report for the selected date range."""
        employee = self._employee()
        today = date.today()
        start_date, end_date = self._parse_dates(
            kw.get('start_date'), kw.get('end_date'),
            default_start=today.replace(day=1), default_end=today)

        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date + timedelta(days=1)),
        ], order='check_in')

        if not attendances:
            return request.redirect('/attendance/')

        c_data = {}
        for att in attendances:
            c_data[att.id] = {
                'emp': att.employee_id.name,
                'checkin': self._local_dt(att.check_in),
                'checkout': self._local_dt(att.check_out),
                'workhours': att.worked_hours,
                'location': att.work_location_id.name or '',
                'geo_verified': att.geo_verified,
            }

        data = {
            'c_data': c_data,
            'employee': employee,
            'start_date': start_date,
            'end_date': end_date,
            'total_hours': sum(attendances.mapped('worked_hours')),
            'company': request.env.company,
        }
        pdf, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'wb_portal.attendance_report_portal',
            res_ids=attendances.ids,
            data=data,
        )
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition',
             'attachment; filename="attendance_report_%s_%s.pdf"' % (
                 start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))),
        ]
        return request.make_response(pdf, headers=headers)

    # ------------------------------------------------------------------
    # Payslips (requires the Enterprise hr_payroll module)
    # ------------------------------------------------------------------
    def _payslip_available(self):
        return 'hr.payslip' in request.env

    @http.route('/payslip/', website=True, auth='user', type='http')
    def employeepayslipdata(self, **post):
        employee = self._employee()
        if not self._payslip_available():
            return request.render(
                'wb_portal.module_unavailable_template',
                self._base_values('wb_payslip', _('My Payslips'), _('Payslips')))

        today = date.today()
        start_date, end_date = self._parse_dates(
            post.get('start_date'), post.get('end_date'),
            default_start=today.replace(day=1), default_end=today)

        payslips = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', start_date),
            ('date_from', '<=', end_date),
        ], order='date_from desc')

        vals = self._base_values('wb_payslip', _('My Payslips'), _('Payslips'))
        vals.update({
            'payslips': payslips,
            'start_date': start_date,
            'end_date': end_date,
        })
        return request.render('wb_portal.my_payslip', vals)

    @http.route('/payslipdetail/', website=True, auth='user')
    def employeePayDisplay(self, **get):
        employee = self._employee()
        if not self._payslip_available():
            return request.render(
                'wb_portal.module_unavailable_template',
                self._base_values('wb_payslip', _('My Payslips'), _('Payslips')))

        try:
            slip = request.env['hr.payslip'].sudo().browse(int(get.get('pay_id')))
        except (TypeError, ValueError):
            return request.redirect('/payslip/')
        if not slip.exists() or slip.employee_id.id != employee.id:
            return request.redirect('/payslip/')

        vals = self._base_values(
            'wb_payslip_detail', _('Payslip Detail'),
            _('Payslip') + ' / %s' % (slip.number or _('Draft')))
        vals.update({'slip': slip})
        return request.render('wb_portal.payslip_detail', vals)

    @http.route('/payslip/print/', website=True, auth='user', type='http')
    def print_report_file(self, **get):
        employee = self._employee()
        if not self._payslip_available():
            return request.redirect('/payslip/')

        try:
            slip = request.env['hr.payslip'].sudo().browse(int(get.get('pay_id')))
        except (TypeError, ValueError):
            return request.redirect('/payslip/')

        if not slip.exists() or slip.employee_id.id != employee.id:
            return request.redirect('/payslip/')

        # Corrected: Use the report action ID, not the view template ID
        report_ref = 'hr_payroll.action_report_payslip'

        if not request.env.ref(report_ref, raise_if_not_found=False):
            vals = self._base_values('wb_payslip', _('My Payslips'), _('Payslips'))
            vals['message'] = _('No payslip PDF report is configured on this '
                                'installation (expected "hr_payroll.action_report_payslip").')
            return request.render('wb_portal.module_unavailable_template', vals)

        return self._show_report(model=slip, report_type='pdf',
                                 report_ref=report_ref, download=True)
    # ------------------------------------------------------------------
    # Time Off
    # ------------------------------------------------------------------
    @http.route('/leaveform/', website=True, auth='user', type='http')
    def empoyeeLeaveForm(self, **post):
        employee = self._employee()
        leave_types = request.env['hr.leave.type'].sudo().search([
            '|',
            ('requires_allocation', '=', 'no'),
            ('has_valid_allocation', '=', True),
        ], order='sequence, name')

        leave_type_data = []
        for lt in leave_types:
            leave_type_data.append({
                'id': lt.id,
                'name': lt.name,
                'remaining': lt.virtual_remaining_leaves or 0,
                'unit': self._unit_label(lt.request_unit),
            })

        leaves = request.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee.id)], order='date_from desc')

        vals = self._base_values('wb_leave_form', _('Apply for Time Off'), _('Time Off'))
        vals.update({
            'leave_type_data': leave_type_data,
            'leaves': leaves,
            'manager': employee.leave_manager_id,
            'error': post.get('error'),
        })
        return request.render('wb_portal.portal_apply_leave', vals)

    @http.route('/leavesave/', website=True, auth='user', type='http', methods=['POST'])
    def employeeLeaveSave(self, **post):
        employee = self._employee()
        start_date = post.get('start_date')
        end_date = post.get('end_date')
        leave_type = post.get('leave_type')
        reason = (post.get('reason') or '').strip()

        error = False
        if not start_date or not end_date:
            error = _('Please select both the "Leave From" and "Leave To" dates.')
        elif not leave_type:
            error = _('Please select a leave type.')
        else:
            try:
                start_date = datetime.strptime(start_date, DF).date()
                end_date = datetime.strptime(end_date, DF).date()
            except (ValueError, TypeError):
                error = _('The dates you entered are not valid.')
            else:
                if end_date < start_date:
                    error = _('The "Leave To" date cannot be before the "Leave From" date.')

        if error:
            return request.redirect('/leaveform/?error=%s' % urllib.parse.quote(error))

        values = {
            'employee_id': employee.id,
            'holiday_status_id': int(leave_type),
            'date_from': datetime.combine(start_date, datetime.min.time()),
            'date_to': datetime.combine(end_date, datetime.min.time()),
            'request_date_from': start_date,
            'request_date_to': end_date,
            'name': reason or _('Time Off Request'),
        }
        try:
            request.env['hr.leave'].sudo().create(values)
        except (AccessError, UserError, ValidationError) as exc:
            return request.redirect('/leaveform/?error=%s' % urllib.parse.quote(str(exc)))
        return request.redirect('/leaveview/')

    @http.route('/leaveview/', website=True, auth='user', type='http')
    def LeaveViewPage(self, **kw):
        employee = self._employee()
        leaves = request.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee.id)], order='date_from desc')
        vals = self._base_values('wb_my_leaves', _('My Time Off'), _('Time Off'))
        vals.update({'leaves': leaves})
        return request.render('wb_portal.leave_view_display', vals)

    @http.route('/leavesapproval/', website=True, auth='user', type='http')
    def LeaveApprovalPage(self, **kw):
        if not self._is_leave_manager():
            return request.redirect('/home/')
        leaves = request.env['hr.leave'].sudo().search(
            [('state', 'in', ['confirm', 'validate1'])], order='date_from')
        vals = self._base_values('wb_leaves_approval', _('Leaves to Approve'), _('Approval'))
        vals.update({'leaves': leaves})
        return request.render('wb_portal.leaves_approval_display', vals)

    @http.route('/leavesdisplay/', website=True, auth='user', type='http')
    def AlleavesDisplay(self, **kw):
        if not request.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            return request.redirect('/home/')
        leaves = request.env['hr.leave'].sudo().search([], order='date_from desc')
        vals = self._base_values('wb_all_leaves', _('All Time Off'), _('Time Off'))
        vals.update({'leaves': leaves})
        return request.render('wb_portal.all_leaves_display', vals)

    @http.route(['/leave/approve/<model("hr.leave"):leave>'], type='http', auth='user', website=True)
    def hr_holidays_request_approve(self, leave, **kw):
        if self._is_leave_manager() and leave:
            leave.sudo().action_approve()
            if leave.state == 'validate1':
                leave.sudo().action_validate()
        return request.redirect('/leavesapproval/')

    @http.route(['/leave/refuse/<model("hr.leave"):leave>'], type='http', auth='user', website=True)
    def hr_holidays_request_refuse(self, leave, **kw):
        if self._is_leave_manager() and leave:
            leave.sudo().action_refuse()
        return request.redirect('/leavesapproval/')

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    @http.route('/documents/', website=True, auth='user', type='http')
    def AllDocument(self, **kw):
        if 'documents.document' not in request.env:
            return request.render(
                'wb_portal.module_unavailable_template',
                self._base_values('wb_documents', _('My Documents'), _('Documents')))
        documents = request.env['documents.document'].sudo().search(
            [('owner_id', '=', request.env.uid)], order='create_date desc')
        vals = self._base_values('wb_documents', _('My Documents'), _('Documents'))
        vals.update({'documents': documents})
        return request.render('wb_portal.all_documents_display', vals)

    # Changed route URL to avoid conflict with Odoo's built-in documents app
    # Changed route URL to avoid conflict with Odoo's built-in documents app
    @http.route('/my_documents/upload/', type='http', auth='user', methods=['POST'], website=True)
    def upload_document(self, **post):
        uploaded_file = post.get('file')
        if not uploaded_file:
            return request.redirect('/documents/')

        content = uploaded_file.read()
        # Ensure MAX_FILE_SIZE is defined in your file, e.g., MAX_FILE_SIZE = 2 * 1024 * 1024
        if len(content) > MAX_FILE_SIZE:
            vals = self._base_values('wb_documents', _('My Documents'), _('Documents'))
            vals['message'] = _('File size should be less than 2 MB.')
            return request.render('wb_portal.invalid_size_template', vals)

        _, file_extension = os.path.splitext(uploaded_file.filename or '')
        # Ensure ALLOWED_EXTENSIONS is defined in your file
        if file_extension.lower() not in ALLOWED_EXTENSIONS:
            vals = self._base_values('wb_documents', _('My Documents'), _('Documents'))
            vals['message'] = _('Invalid file extension. Allowed extensions are: %s.') % (
                ', '.join(ALLOWED_EXTENSIONS))
            return request.render('wb_portal.invalid_extension_template', vals)

        folder = request.env.ref('documents.document_workspace_main', raise_if_not_found=False)
        if not folder:
            folder = request.env['documents.document'].sudo().search([('type', '=', 'folder')], limit=1)

        document_vals = {
            'name': uploaded_file.filename,
            'raw': content,
            'type': 'binary',
            'owner_id': request.env.uid,
            'folder_id': folder.id if folder else False,
        }

        request.env['documents.document'].sudo().create(document_vals)
        return request.redirect('/documents/')

    @http.route('/web/binary/download_document', type='http', auth='public')
    def download_document(self, **kwargs):
        try:
            doc_id = int(kwargs.get('doc_id'))
        except (TypeError, ValueError):
            return request.not_found()
        document = request.env['documents.document'].sudo().browse(doc_id)
        if not document.exists() or not document.raw:
            return request.not_found()
        return request.make_response(
            document.raw,
            [
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', 'attachment; filename="%s"' % document.name),
            ])
