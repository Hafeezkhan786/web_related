# -*- coding: utf-8 -*-
"""Employee loans for the WB HR Employee Portal (Odoo 18).

Odoo does not ship a native "accounting loans" module in 18, so this module
provides a clean, secure `wb.loan` model with a portal application flow and
backend approval workflow. The portal controller is written so it can also
work against an existing `hr.loan` model (common community loan apps) when
one is installed — see `controllers/extras.py`.
"""
from odoo import api, fields, models


class WBPortalLoan(models.Model):
    _name = 'wb.loan'
    _description = 'HR Portal Loan'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Reference', required=True, readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('wb.loan.seq'))
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True,
        ondelete='cascade', index=True)
    user_id = fields.Many2one(
        'res.users', string='User', related='employee_id.user_id',
        related_sudo=True, store=True, index=True)
    date = fields.Date(string='Request Date', default=fields.Date.context_today,
                       required=True)
    loan_type = fields.Selection([
        ('personal', 'Personal'),
        ('medical', 'Medical'),
        ('education', 'Education'),
        ('vehicle', 'Vehicle'),
        ('house', 'House'),
        ('other', 'Other'),
    ], string='Loan Type', default='personal', required=True)
    amount = fields.Monetary(
        string='Loan Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id)
    installments = fields.Integer(
        string='Number of Installments', required=True, default=12,
        help='Over how many monthly installments the loan will be repaid.')
    installment_amount = fields.Monetary(
        string='Installment Amount', currency_field='currency_id',
        compute='_compute_installment_amount')
    reason = fields.Text(string='Reason / Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    approved_by = fields.Many2one('res.users', string='Approved By',
                                  readonly=True, copy=False)
    approval_date = fields.Datetime(string='Approval Date', readonly=True,
                                    copy=False)
    refusal_reason = fields.Text(string='Refusal Reason', readonly=True,
                                 copy=False)
    paid_amount = fields.Monetary(
        string='Paid Amount', currency_field='currency_id', default=0,
        help='Total amount already reimbursed/paid back.')
    remaining_amount = fields.Monetary(
        string='Remaining Balance', currency_field='currency_id',
        compute='_compute_remaining_amount')

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)',
         'The loan amount must be positive.'),
        ('installments_positive', 'CHECK(installments > 0)',
         'The number of installments must be at least 1.'),
    ]

    @api.depends('amount', 'installments')
    def _compute_installment_amount(self):
        for loan in self:
            loan.installment_amount = (
                loan.amount / loan.installments if loan.installments else 0)

    @api.depends('amount', 'paid_amount')
    def _compute_remaining_amount(self):
        for loan in self:
            loan.remaining_amount = max(loan.amount - (loan.paid_amount or 0), 0)

    # ------------------------------------------------------------------
    # Workflow (backend, HR side)
    # ------------------------------------------------------------------
    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        for loan in self:
            loan.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })

    def action_refuse(self, reason=False):
        for loan in self:
            loan.write({
                'state': 'refused',
                'refusal_reason': reason,
            })

    def action_cancel(self):
        self.state = 'cancelled'

    def action_mark_paid(self):
        self.state = 'paid'
        self.paid_amount = self.amount
