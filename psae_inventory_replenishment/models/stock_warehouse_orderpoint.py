# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    qty_delivered_current_month_display = fields.Char(
        string='Curr Mnt Qty',
        compute='_compute_qty_delivered_current_month',
        store=False,
        readonly=True,
        help='Total delivered quantity in the current month with unit of measure'
    )

    qty_to_deliver_display = fields.Char(
        string='Lst 2mnt Avg Sale',
        compute='_compute_qty_delivered_2months',
        store=False,
        readonly=True,
        help='Total delivered/sold quantity in the last 2 months with unit of measure'
    )

    @api.depends('product_id', 'product_uom')
    def _compute_qty_delivered_2months(self):
        # Calculate date_from as the 1st of 2 months ago
        # Calculate date_to as the 1st of current month to include full previous 2 months
        today = fields.Date.today()
        date_from = (today - relativedelta(months=2)).replace(day=1)
        date_to = today.replace(day=1)
        product_ids = [rec.product_id.id for rec in self if rec.product_id]

        so_delivered_map = {}
        stock_delivered_map = {}

        if product_ids:
            # 1. Query sale.report with sudo() to bypass security checks
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

        for rec in self:
            if rec.product_id:
                pid = rec.product_id.id
                # Prioritize sale.report / SO delivered qty; fallback to stock moves
                total_2months_qty = so_delivered_map.get(pid) if pid in so_delivered_map else stock_delivered_map.get(pid, 0.0)
                # Divide 2-month total by 2 to display average monthly quantity
                qty = total_2months_qty / 2.0
                uom_name = rec.product_id.uom_id.name or (rec.product_uom.name if rec.product_uom else '') or ''
                formatted_qty = f"{int(qty)}" if qty == int(qty) else f"{qty:g}"
                rec.qty_to_deliver_display = f"{formatted_qty} {uom_name}".strip() if uom_name else formatted_qty
            else:
                rec.qty_to_deliver_display = "0"

    @api.depends('product_id', 'product_uom')
    def _compute_qty_delivered_current_month(self):
        # Calculate cur_month_start as the 1st of the current month
        today = fields.Date.today()
        cur_month_start = today.replace(day=1)
        product_ids = [rec.product_id.id for rec in self if rec.product_id]

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

        for rec in self:
            if rec.product_id:
                pid = rec.product_id.id
                qty = so_delivered_map.get(pid) if pid in so_delivered_map else stock_delivered_map.get(pid, 0.0)
                uom_name = rec.product_id.uom_id.name or (rec.product_uom.name if rec.product_uom else '') or ''
                formatted_qty = f"{int(qty)}" if qty == int(qty) else f"{qty:g}"
                rec.qty_delivered_current_month_display = f"{formatted_qty} {uom_name}".strip() if uom_name else formatted_qty
            else:
                rec.qty_delivered_current_month_display = "0"

