from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """
        Ensure payment transaction post-processing carries context
        so linked website sale orders are not automatically moved to
        'sent' or 'sale' state.
        """
        res = super(
            PaymentTransaction,
            self.with_context(from_payment_post_process=True)
        )._post_process()

        # Safety check: force website sale orders linked to transactions back to draft if changed, ONLY IF not already confirmed/done/cancelled
        website_orders = self.sale_order_ids.filtered(
            lambda so: so.website_id and so.state not in ('sale', 'done', 'cancel')
        )
        for order in website_orders:
            if order.state != 'draft':
                order.sudo().with_context(
                    tracking_disable=True,
                    mail_notrack=True,
                    no_recompute=True,
                ).write({'state': 'draft'})

        return res

    def _check_amount_and_confirm_order(self):
        """
        Prevent website checkout sale orders (orders with website_id set)
        from being automatically confirmed to 'sale' state when transactions
        become 'done' or 'authorized' during post-processing.
        """
        txs_to_confirm = self.filtered(
            lambda tx: not any(so.website_id for so in tx.sale_order_ids)
        )
        return super(
            PaymentTransaction,
            txs_to_confirm
        )._check_amount_and_confirm_order()
