# -*- coding: utf-8 -*-
"""ESS portal extras: Planning, Announcements, Events, Expenses, Loans (Odoo 18).

Security model: every read is executed with `sudo()` but always filtered by
the logged-in user's employee, every detail view re-checks ownership, and
every create forces `employee_id` from the session user server-side (never
from the posted form). Record rules are provided for the models this module
owns (`wb.loan`); for native modules (planning/event/hr_expense) the
controller-level domain filtering is the enforcement layer, which avoids
interfering with the backend access rules of those apps.
"""
import calendar
from datetime import datetime, timedelta

from odoo import _, fields as odoo_fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.wb_portal.controllers.main import WBEmployeePortal


class WBPortalExtras(WBEmployeePortal, http.Controller):
    """Planning / Announcements / Events / Expenses / Loans."""

    # ------------------------------------------------------------------
    # 1. PLANNING (Enterprise `planning` module)
    # ------------------------------------------------------------------
    @http.route('/planning/', website=True, auth='user', type='http')
    def my_planning(self, **post):
        employee = self._employee()
        if 'planning.slot' not in request.env:
            vals = self._base_values(
                'wb_planning', _('My Planning'), _('Planning'))
            vals['message'] = _(
                'The Planning module is not installed on this database '
                '(it is part of Odoo Enterprise).')
            return request.render('wb_portal.module_unavailable_template', vals)

        today = datetime.now()
        # Period selector: 'week' or 'month'
        period = post.get('period', 'week')
        if period not in ('week', 'month'):
            period = 'week'
        # Selected date (default: today) -> anchor of the period
        try:
            anchor = odoo_fields.Datetime.to_datetime(
                odoo_fields.Datetime.context_timestamp(
                    request.env.user, odoo_fields.Datetime.now()))
        except Exception:
            anchor = today
        if period == 'week':
            start = anchor - timedelta(days=anchor.weekday())  # Monday
            start = start.replace(hour=0, minute=0, second=0)
            end = start + timedelta(days=7)
            period_label = _('Week of %s') % start.strftime('%d-%m-%Y')
        else:
            start = anchor.replace(day=1, hour=0, minute=0, second=0)
            end = (start + timedelta(days=32)).replace(day=1)
            period_label = '%s %s' % (
                calendar.month_name[start.month], start.year)

        Slot = request.env['planning.slot'].sudo()
        slots = Slot.search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>=', start),
            ('start_datetime', '<', end),
        ], order='start_datetime')

        slot_data = []
        for slot in slots:
            role = slot.role_id.name if 'role_id' in slot._fields and slot.role_id else ''
            state = slot.state if 'state' in slot._fields else False
            slot_data.append({
                'id': slot.id,
                'start': self._local_dt(slot.start_datetime),
                'end': self._local_dt(slot.end_datetime),
                'role': role or '',
                'state': state,
                'task': slot.task_id.name if 'task_id' in slot._fields and slot.task_id else '',
                'project': slot.project_id.name if 'project_id' in slot._fields and slot.project_id else '',
                'notes': slot.notes if 'notes' in slot._fields else '',
            })

        vals = self._base_values('wb_planning', _('My Planning'), _('Planning'))
        vals.update({
            'slot_data': slot_data,
            'period': period,
            'period_label': period_label,
            'start_date': start.date(),
            'end_date': end.date(),
        })
        return request.render('wb_portal.my_planning', vals)

    # ------------------------------------------------------------------
    # 2. ANNOUNCEMENTS (Discuss channel messages)
    # ------------------------------------------------------------------
    def _get_announcement_channel(self):
        """Resolve the announcements channel:
        1. ir.config_parameter `wb_portal.announcement_channel_id` (set by admin)
        2. first public 'channel' named General / Announcements / Staff
        """
        Channel = request.env['discuss.channel'].sudo()
        param = request.env['ir.config_parameter'].sudo().get_param(
            'wb_portal.announcement_channel_id', False)
        if param:
            try:
                channel = Channel.browse(int(param))
                if channel.exists():
                    return channel
            except (TypeError, ValueError):
                pass
        names = ['Announcements', 'General', 'Staff', 'Company News']
        base_domain = [('channel_type', '=', 'channel')]
        # 1) exact name match first
        for name in names:
            channel = Channel.search(
                base_domain + [('name', '=', name)], order='id', limit=1)
            if channel:
                return channel
        # 2) case-insensitive contains
        for name in names:
            channel = Channel.search(
                base_domain + [('name', 'ilike', name)], order='id', limit=1)
            if channel:
                return channel
        # 3) fall back to any public channel
        return Channel.search(base_domain, order='id', limit=1)

    @http.route('/announcements/', website=True, auth='user', type='http')
    def announcements(self, **post):
        channel = self._get_announcement_channel()
        announcements = []

        if channel:
            # Pinned messages first (treated as official announcements)
            pinned = channel.pinned_message_ids.sudo().sorted(
                key=lambda m: m.date, reverse=True)
            # Then recent comment / notification messages
            recent = request.env['mail.message'].sudo().search([
                ('model', '=', 'discuss.channel'),
                ('res_id', '=', channel.id),
                ('message_type', 'in', ['comment', 'notification']),
                ('id', 'not in', pinned.ids),
            ], order='date desc', limit=30)

            for msg in (pinned + recent):
                body = msg.body or ''
                # strip html tags for a plain summary, keep html for display
                author = msg.author_id.name or (
                    msg.author_id.sudo().name or _('Unknown'))
                announcements.append({
                    'id': msg.id,
                    'subject': msg.subject or _('Announcement'),
                    'body_html': body,
                    'author': author,
                    'date': self._local_dt(msg.date),
                    'pinned': msg in pinned,
                })

        vals = self._base_values(
            'wb_announcements', _('Announcements'), _('Announcements'))
        vals.update({
            'channel': channel,
            'announcements': announcements,
        })
        return request.render('wb_portal.my_announcements', vals)

    # ------------------------------------------------------------------
    # 3. EVENTS (native `event` module)
    # ------------------------------------------------------------------
    @http.route('/events/', website=True, auth='user', type='http')
    def my_events(self, **post):
        employee = self._employee()
        if 'event.event' not in request.env:
            vals = self._base_values('wb_events', _('Events'), _('Events'))
            vals['message'] = _('The Events module is not installed on this database.')
            return request.render('wb_portal.module_unavailable_template', vals)

        Event = request.env['event.event'].sudo()
        domain = [
            ('date_begin', '>=', datetime.now()),
            ('active', '=', True),
        ]
        # Only show published events when the website mixin provides the flag
        if 'is_published' in Event._fields:
            domain.append(('is_published', '=', True))
        events = Event.search(domain, order='date_begin', limit=30)

        event_data = []
        for event in events:
            event_data.append({
                'id': event.id,
                'name': event.name,
                'date_begin': self._local_dt(event.date_begin),
                'date_end': self._local_dt(event.date_end),
                'address': event.address_id.name if event.address_id else '',
                'event_type': event.event_type_id.name if event.event_type_id else '',
                'seats_available': event.seats_available if 'seats_available' in event._fields else 0,
                'description': event.description or '',
            })

        vals = self._base_values('wb_events', _('Events'), _('Events'))
        vals.update({'event_data': event_data})
        return request.render('wb_portal.my_events', vals)

    # ------------------------------------------------------------------
    # 4. EXPENSES (native `hr_expense` module)
    # ------------------------------------------------------------------
    def _expense_available(self):
        return 'hr.expense' in request.env

    @http.route('/expenses/', website=True, auth='user', type='http')
    def my_expenses(self, **post):
        employee = self._employee()
        if not self._expense_available():
            vals = self._base_values('wb_expenses', _('Expenses'), _('Expenses'))
            vals['message'] = _('The Expenses module is not installed on this database.')
            return request.render('wb_portal.module_unavailable_template', vals)

        expenses = request.env['hr.expense'].sudo().search(
            [('employee_id', '=', employee.id)], order='date desc')

        expense_data = []
        for exp in expenses:
            expense_data.append({
                'id': exp.id,
                'name': exp.name,
                'date': exp.date,
                'amount': exp.total_amount,
                'currency': exp.currency_id.symbol or exp.currency_id.name,
                'state': exp.state,
                'sheet': exp.sheet_id.name if exp.sheet_id else '',
            })

        # Expense products (categories) the employee can pick from
        expense_products = request.env['product.product'].sudo().search(
            [('can_be_expensed', '=', True)], order='name', limit=50)
        product_data = [{
            'id': p.id,
            'name': p.display_name,
            'price': p.lst_price,
        } for p in expense_products]

        vals = self._base_values('wb_expenses', _('Expenses'), _('Expenses'))
        vals.update({
            'expense_data': expense_data,
            'expense_products': product_data,
            'today': odoo_fields.Date.today(),
            'error': post.get('error'),
        })
        return request.render('wb_portal.my_expenses', vals)

    @http.route('/expenses/new/', website=True, auth='user', type='http',
                methods=['POST'])
    def expense_new(self, **post):
        employee = self._employee()
        if not self._expense_available():
            return request.redirect('/expenses/')

        name = (post.get('name') or '').strip()
        date = post.get('date')
        amount = post.get('amount')
        quantity = post.get('quantity') or '1'
        product_id = post.get('product_id')

        error = False
        if not name:
            error = _('Please enter a description for the expense.')
        else:
            try:
                amount = float(amount or 0)
                quantity = float(quantity or 1)
                if amount <= 0:
                    error = _('The amount must be greater than zero.')
            except (TypeError, ValueError):
                error = _('The amount you entered is not valid.')

        if not date:
            date = odoo_fields.Date.today()

        if error:
            return request.redirect(
                '/expenses/?error=%s' % error)

        # price_unit + total_amount must be passed together: the model's
        # _compute_price_unit divides total_amount by quantity when there is
        # no product, so a lone price_unit would be recomputed from 0.
        vals = {
            'employee_id': employee.id,
            'name': name,
            'date': date,
            'price_unit': amount,
            'quantity': quantity,
            'total_amount': amount * quantity,
        }
        if product_id:
            try:
                vals['product_id'] = int(product_id)
            except (TypeError, ValueError):
                pass

        try:
            request.env['hr.expense'].sudo().create(vals)
        except (AccessError, UserError, ValidationError) as exc:
            return request.redirect('/expenses/?error=%s' % exc)
        return request.redirect('/expenses/')

    # ------------------------------------------------------------------
    # 5. LOANS (wb.loan, or an existing hr.loan model)
    # ------------------------------------------------------------------
    def _loan_model_name(self):
        if 'hr.loan' in request.env:
            return 'hr.loan'
        return 'wb.loan'

    def _loan_to_dict(self, loan, model):
        fields_ = model._fields
        state = loan.state if 'state' in fields_ else False
        amount = loan.loan_amount if 'loan_amount' in fields_ else (
            loan.amount if 'amount' in fields_ else 0)
        currency = loan.currency_id if 'currency_id' in fields_ else False
        return {
            'id': loan.id,
            'name': loan.name or loan.display_name,
            'date': loan.date if 'date' in fields_ else False,
            'amount': amount,
            'currency': currency.symbol if currency else '',
            'state': state,
            'reason': loan.reason if 'reason' in fields_ else (
                loan.description if 'description' in fields_ else ''),
            'installments': loan.installments if 'installments' in fields_ else 0,
            'loan_type': loan.loan_type if 'loan_type' in fields_ else False,
        }

    @http.route('/loans/', website=True, auth='user', type='http')
    def my_loans(self, **post):
        employee = self._employee()
        model_name = self._loan_model_name()
        model = request.env[model_name].sudo()
        loans = model.search([('employee_id', '=', employee.id)],
                             order='date desc, id desc')
        loan_data = [self._loan_to_dict(l, model) for l in loans]

        vals = self._base_values('wb_loans', _('Loans'), _('Loans'))
        vals.update({
            'loan_data': loan_data,
            'is_custom_loan': model_name == 'wb.loan',
            'error': post.get('error'),
        })
        return request.render('wb_portal.my_loans', vals)

    @http.route('/loans/new/', website=True, auth='user', type='http',
                methods=['POST'])
    def loan_new(self, **post):
        employee = self._employee()
        model_name = self._loan_model_name()
        model = request.env[model_name].sudo()

        loan_type = post.get('loan_type')
        amount = post.get('amount')
        installments = post.get('installments') or '12'
        reason = (post.get('reason') or '').strip()

        error = False
        try:
            amount = float(amount or 0)
            installments = int(installments or 0)
            if amount <= 0:
                error = _('The loan amount must be greater than zero.')
            if installments <= 0:
                error = _('The number of installments must be at least 1.')
        except (TypeError, ValueError):
            error = _('The amount or installments you entered are not valid.')

        if error:
            return request.redirect('/loans/?error=%s' % error)

        vals = {
            'employee_id': employee.id,
            'amount': amount,
            'installments': installments,
            'reason': reason,
        }
        if model_name == 'wb.loan':
            vals.update({
                'loan_type': loan_type or 'personal',
                'state': 'submitted',
            })
        elif 'loan_type' in model._fields and loan_type:
            vals['loan_type'] = loan_type

        try:
            model.create(vals)
        except (AccessError, UserError, ValidationError) as exc:
            return request.redirect('/loans/?error=%s' % exc)
        return request.redirect('/loans/')

    # ------------------------------------------------------------------
    # 6. HELP DESK — complaints & suggestions (native `helpdesk`, Enterprise)
    # ------------------------------------------------------------------
    def _helpdesk_available(self):
        """Helpdesk is usable as soon as the ticket model exists.

        The team model is resolved separately (`_helpdesk_team_model`) because
        different helpdesk implementations / versions name it differently
        (e.g. `helpdesk.ticket.team` vs `helpdesk.team`) — it must never make
        the page crash when missing.
        """
        return 'helpdesk.ticket' in request.env

    def _helpdesk_team_model(self):
        """Resolve the helpdesk team model name (or False)."""
        try:
            ticket_model = request.env['helpdesk.ticket']
        except KeyError:
            return False
        # 1) canonical: the comodel of the ticket's team_id field
        team_field = ticket_model._fields.get('team_id')
        if team_field and team_field.comodel_name in request.env:
            return team_field.comodel_name
        # 2) known model names
        for name in ('helpdesk.ticket.team', 'helpdesk.team'):
            if name in request.env:
                return name
        return False

    def _helpdesk_teams(self):
        """Teams the employee may submit a ticket to (website-enabled first).

        Never raises: returns an empty recordset when no team model exists.
        """
        model_name = self._helpdesk_team_model()
        if not model_name:
            return request.env['res.partner']  # empty recordset stand-in
        try:
            Team = request.env[model_name].sudo()
            domain = [('active', '=', True)] if 'active' in Team._fields else []
            if 'use_website' in Team._fields:
                website_teams = Team.search(
                    domain + [('use_website', '=', True)],
                    order='sequence, name')
                if website_teams:
                    return website_teams
            return Team.search(domain, order='sequence, name')
        except Exception:
            return request.env['res.partner']

    def _helpdesk_ticket_to_dict(self, ticket):
        fields_ = ticket._fields
        state = ticket.state if 'state' in fields_ else False
        priority = ticket.priority if 'priority' in fields_ else False
        # Resolve the selection label for the priority (never show raw keys)
        if priority not in (False, None) and 'priority' in fields_ and fields_['priority'].selection:
            priority = dict(fields_['priority'].selection).get(priority, priority)
        return {
            'id': ticket.id,
            'name': ticket.name,
            'team': ticket.team_id.name if ticket.team_id else '',
            'stage': ticket.stage_id.name if ticket.stage_id else '',
            'state': state,
            'priority': priority,
            'create_date': self._local_dt(ticket.create_date) if ticket.create_date else False,
            'description': ticket.description if 'description' in fields_ else False,
        }

    @http.route('/helpdesk/', website=True, auth='user', type='http')
    def my_helpdesk(self, **post):
        if not self._helpdesk_available():
            vals = self._base_values('wb_helpdesk', _('Helpdesk'), _('Helpdesk'))
            vals['message'] = _(
                'The Helpdesk module is not installed on this database '
                '(it is part of Odoo Enterprise).')
            return request.render('wb_portal.module_unavailable_template', vals)

        Ticket = request.env['helpdesk.ticket'].sudo()
        partner = request.env.user.partner_id

        # State filter (dropdown)
        state_filter = post.get('state') or 'all'
        state_options = []
        if 'state' in Ticket._fields and Ticket._fields['state'].selection:
            state_options = [
                {'key': key, 'label': label}
                for key, label in Ticket._fields['state'].selection
            ]
        if state_filter not in ('all',) and not any(
                o['key'] == state_filter for o in state_options):
            state_filter = 'all'

        domain = [('partner_id', '=', partner.id)]
        if state_filter != 'all':
            domain.append(('state', '=', state_filter))
        tickets = Ticket.search(domain, order='create_date desc')

        # Priority selection options for the create form
        priority_options = []
        if 'priority' in Ticket._fields and Ticket._fields['priority'].selection:
            priority_options = [
                {'key': key, 'label': label}
                for key, label in Ticket._fields['priority'].selection
            ]

        teams = self._helpdesk_teams()
        vals = self._base_values('wb_helpdesk', _('Helpdesk'), _('Helpdesk'))
        vals.update({
            'tickets': [self._helpdesk_ticket_to_dict(t) for t in tickets],
            'teams': [{'id': t.id, 'name': t.name} for t in teams],
            'has_teams': bool(teams),
            'priority_options': priority_options,
            'state_options': state_options,
            'state_filter': state_filter,
            'error': post.get('error'),
        })
        return request.render('wb_portal.my_helpdesk', vals)

    @http.route('/helpdesk/new/', website=True, auth='user', type='http',
                methods=['POST'])
    def helpdesk_new(self, **post):
        if not self._helpdesk_available():
            return request.redirect('/helpdesk/')

        partner = request.env.user.partner_id
        name = (post.get('subject') or '').strip()
        team_id = post.get('team_id')
        priority = post.get('priority')
        description = (post.get('description') or '').strip()

        teams = self._helpdesk_teams()
        error = False
        if not name:
            error = _('Please enter a subject for your ticket.')
        elif not teams:
            error = _('No helpdesk team is available on this database yet.')
        elif not team_id:
            error = _('Please select a team.')
        if not error and team_id:
            try:
                team_id = int(team_id)
            except (TypeError, ValueError):
                error = _('Please select a valid team.')
            else:
                if team_id not in teams.ids:
                    error = _('Please select a valid team.')

        if error:
            return request.redirect('/helpdesk/?error=%s' % error)

        vals = {
            'name': name,
            'partner_id': partner.id,
            'team_id': team_id,
            # 'email_from': partner.email or request.env.user.login or False,
            'description': description,
        }
        if priority:
            vals['priority'] = priority

        try:
            request.env['helpdesk.ticket'].sudo().create(vals)
        except (AccessError, UserError, ValidationError) as exc:
            return request.redirect('/helpdesk/?error=%s' % exc)
        return request.redirect('/helpdesk/')

    @http.route('/helpdesk/<int:ticket_id>', website=True, auth='user',
                type='http')
    def helpdesk_detail(self, ticket_id, **post):
        if not self._helpdesk_available():
            return request.redirect('/helpdesk/')

        partner = request.env.user.partner_id
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id).exists()
        if not ticket or ticket.partner_id.id != partner.id:
            return request.redirect('/helpdesk/')

        # Conversation (mail.thread), oldest first
        messages = []
        if 'message_ids' in ticket._fields:
            for msg in ticket.message_ids.sorted(key=lambda m: m.date):
                messages.append({
                    'author': msg.author_id.name or _('Unknown'),
                    'date': self._local_dt(msg.date),
                    'body': msg.body or '',
                })

        vals = self._base_values(
            'wb_helpdesk_detail', _('Helpdesk'), _('Helpdesk'))
        vals.update({
            'ticket': self._helpdesk_ticket_to_dict(ticket),
            'messages': messages,
        })
        return request.render('wb_portal.helpdesk_detail', vals)
