# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    free_qty_today = fields.Float(
        string="On Bond Qty",
        compute="_compute_free_qty_today",
        digits="Product Unit of Measure",
        help="Available free stock quantity for this product today."
    )
    
    on_hand_qty = fields.Float(
        string="On Hand Qty",
        compute="_compute_on_hand_qty",
        digits="Product Unit of Measure",
        help="Current physical stock on hand for this product."
    )
    on_hand_qty_display = fields.Char(
        string="On Hand Qty",
        compute="_compute_on_hand_qty",
        help="Current physical stock on hand with unit of measure."
    )

    min_qty = fields.Float(
        string="Min Qty",
        compute="_compute_min_max_qty",
        digits="Product Unit of Measure",
        help="Minimum reordering quantity rule for this product."
    )
    max_qty = fields.Float(
        string="Max Qty",
        compute="_compute_min_max_qty",
        digits="Product Unit of Measure",
        help="Maximum reordering quantity rule for this product."
    )
    min_max_qty_display = fields.Char(
        string="Min / Max",
        compute="_compute_min_max_qty",
        help="Minimum and maximum stock rules for this product."
    )

    qty_delivered_2months = fields.Float(
        string="Qty Delivered (2M)",
        compute="_compute_qty_delivered_2months",
        digits="Product Unit of Measure",
        help="Total delivered/sold quantity for this product in the last 2 months."
    )
    qty_to_deliver_display = fields.Char(
        string="Qty Deliver",
        compute="_compute_qty_delivered_2months",
        help="Total delivered/sold quantity in the last 2 months with unit of measure."
    )

    qty_delivered_current_month = fields.Float(
        string="Current Month Delivered Qty",
        compute="_compute_qty_delivered_current_month",
        digits="Product Unit of Measure",
        help="Total delivered/sold quantity for this product in the current month to date."
    )
    qty_delivered_current_month_display = fields.Char(
        string="Current Month Qty",
        compute="_compute_qty_delivered_current_month",
        help="Total delivered/sold quantity in the current month with unit of measure."
    )

    @api.depends('product_id', 'product_id.free_qty')
    def _compute_free_qty_today(self):
        for line in self:
            if line.product_id:
                line.free_qty_today = line.product_id.free_qty
            else:
                line.free_qty_today = 0.0

    @api.depends('product_id', 'product_id.qty_available', 'product_id.uom_id')
    def _compute_on_hand_qty(self):
        for line in self:
            if line.product_id:
                qty = line.product_id.qty_available
                uom_name = line.product_id.uom_id.name or line.product_uom_id.name or ''
                line.on_hand_qty = qty
                formatted_qty = f"{int(qty)}" if qty == int(qty) else f"{qty:g}"
                line.on_hand_qty_display = f"{formatted_qty} {uom_name}".strip() if uom_name else formatted_qty
            else:
                line.on_hand_qty = 0.0
                line.on_hand_qty_display = "0"

    @api.depends('product_id', 'product_id.reordering_min_qty', 'product_id.reordering_max_qty')
    def _compute_min_max_qty(self):
        for line in self:
            if line.product_id:
                min_q = line.product_id.reordering_min_qty
                max_q = line.product_id.reordering_max_qty
                line.min_qty = min_q
                line.max_qty = max_q
                fmt_min = f"{int(min_q)}" if min_q == int(min_q) else f"{min_q:g}"
                fmt_max = f"{int(max_q)}" if max_q == int(max_q) else f"{max_q:g}"
                line.min_max_qty_display = f"Min: {fmt_min} / Max: {fmt_max}"
            else:
                line.min_qty = 0.0
                line.max_qty = 0.0
                line.min_max_qty_display = "Min: 0 / Max: 0"

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_qty_delivered_2months(self):
        # Calculate date_from as the 1st of 2 months ago (e.g. July 1st if current month is September)
        # Calculate date_to as the 1st of current month (e.g. September 1st) to include full previous 2 months (July & August)
        today = fields.Date.today()
        date_from = (today - relativedelta(months=2)).replace(day=1)
        date_to = today.replace(day=1)
        product_ids = [line.product_id.id for line in self if line.product_id]
        
        so_delivered_map = {}
        stock_delivered_map = {}

        if product_ids:
            # 1. Query sale.report (the exact model powering Sales Analysis report) with sudo() to bypass security checks for non-sales users
            if 'sale.report' in self.env:
                domain_sale = [
                    ('product_id', 'in', product_ids),
                    ('state', 'in', ['sale', 'done']),
                    ('date', '>=', date_from),
                    ('date', '<', date_to),
                ]
                report_groupby = self.env['sale.report'].sudo()._read_group(
                    domain_sale, ['product_id'], ['qty_delivered:sum']
                )
                for product, qty_del_sum in report_groupby:
                    if qty_del_sum:
                        so_delivered_map[product.id] = qty_del_sum

            # Fallback to sale.order.line if sale.report returns nothing
            if not so_delivered_map and 'sale.order.line' in self.env:
                domain_sale_line = [
                    ('product_id', 'in', product_ids),
                    ('state', 'in', ['sale', 'done']),
                    ('order_id.date_order', '>=', date_from),
                    ('order_id.date_order', '<', date_to),
                ]
                sol_groupby = self.env['sale.order.line'].sudo()._read_group(
                    domain_sale_line, ['product_id', 'product_uom_id'], ['qty_delivered:sum']
                )
                for product, uom, qty_del_sum in sol_groupby:
                    if qty_del_sum:
                        converted_qty = uom._compute_quantity(qty_del_sum, product.uom_id) if uom and product.uom_id else qty_del_sum
                        so_delivered_map[product.id] = so_delivered_map.get(product.id, 0.0) + converted_qty

            # 2. Query Stock Move Lines as fallback for products without SOs
            domain_stock = [
                ('product_id', 'in', product_ids),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'customer'),
                ('date', '>=', date_from),
                ('date', '<', date_to),
            ]
            moves_groupby = self.env['stock.move.line'].sudo()._read_group(
                domain_stock, ['product_id', 'product_uom_id'], ['quantity:sum']
            )
            for product, uom, qty_sum in moves_groupby:
                if qty_sum:
                    converted_qty = uom._compute_quantity(qty_sum, product.uom_id) if uom and product.uom_id else qty_sum
                    stock_delivered_map[product.id] = stock_delivered_map.get(product.id, 0.0) + converted_qty

        for line in self:
            if line.product_id:
                pid = line.product_id.id
                # Prioritize sale.report / SO delivered qty (matching Sales Analysis report); fallback to stock moves
                total_2months_qty = so_delivered_map.get(pid) if pid in so_delivered_map else stock_delivered_map.get(pid, 0.0)
                # Divide 2-month total quantity by 2 to display average monthly quantity
                qty = total_2months_qty / 2.0
                uom_name = line.product_id.uom_id.name or line.product_uom_id.name or ''
                line.qty_delivered_2months = qty
                formatted_qty = f"{int(qty)}" if qty == int(qty) else f"{qty:g}"
                line.qty_to_deliver_display = f"{formatted_qty} {uom_name}".strip() if uom_name else formatted_qty
            else:
                line.qty_delivered_2months = 0.0
                line.qty_to_deliver_display = "0"

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_qty_delivered_current_month(self):
        # Calculate cur_month_start as the 1st of the current month
        today = fields.Date.today()
        cur_month_start = today.replace(day=1)
        product_ids = [line.product_id.id for line in self if line.product_id]

        so_delivered_map = {}
        stock_delivered_map = {}

        if product_ids:
            # 1. Query sale.report for current month to date with sudo()
            if 'sale.report' in self.env:
                domain_sale = [
                    ('product_id', 'in', product_ids),
                    ('state', 'in', ['sale', 'done']),
                    ('date', '>=', cur_month_start),
                ]
                report_groupby = self.env['sale.report'].sudo()._read_group(
                    domain_sale, ['product_id'], ['qty_delivered:sum']
                )
                for product, qty_del_sum in report_groupby:
                    if qty_del_sum:
                        so_delivered_map[product.id] = qty_del_sum

            # Fallback to sale.order.line if sale.report returns nothing
            if not so_delivered_map and 'sale.order.line' in self.env:
                domain_sale_line = [
                    ('product_id', 'in', product_ids),
                    ('state', 'in', ['sale', 'done']),
                    ('order_id.date_order', '>=', cur_month_start),
                ]
                sol_groupby = self.env['sale.order.line'].sudo()._read_group(
                    domain_sale_line, ['product_id', 'product_uom_id'], ['qty_delivered:sum']
                )
                for product, uom, qty_del_sum in sol_groupby:
                    if qty_del_sum:
                        converted_qty = uom._compute_quantity(qty_del_sum, product.uom_id) if uom and product.uom_id else qty_del_sum
                        so_delivered_map[product.id] = so_delivered_map.get(product.id, 0.0) + converted_qty

            # 2. Query Stock Move Lines as fallback for products without SOs
            domain_stock = [
                ('product_id', 'in', product_ids),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'customer'),
                ('date', '>=', cur_month_start),
            ]
            moves_groupby = self.env['stock.move.line'].sudo()._read_group(
                domain_stock, ['product_id', 'product_uom_id'], ['quantity:sum']
            )
            for product, uom, qty_sum in moves_groupby:
                if qty_sum:
                    converted_qty = uom._compute_quantity(qty_sum, product.uom_id) if uom and product.uom_id else qty_sum
                    stock_delivered_map[product.id] = stock_delivered_map.get(product.id, 0.0) + converted_qty

        for line in self:
            if line.product_id:
                pid = line.product_id.id
                qty = so_delivered_map.get(pid) if pid in so_delivered_map else stock_delivered_map.get(pid, 0.0)
                uom_name = line.product_id.uom_id.name or line.product_uom_id.name or ''
                line.qty_delivered_current_month = qty
                formatted_qty = f"{int(qty)}" if qty == int(qty) else f"{qty:g}"
                line.qty_delivered_current_month_display = f"{formatted_qty} {uom_name}".strip() if uom_name else formatted_qty
            else:
                line.qty_delivered_current_month = 0.0
                line.qty_delivered_current_month_display = "0"
