from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_sent(self):
        """
        Prevent automatic transition from 'draft' to 'sent' state for website sale orders
        during payment transaction post-processing.
        """
        if self.env.context.get('from_payment_post_process') or self.env.user._is_public():
            orders_to_process = self.filtered(lambda so: not so.website_id)
            if not orders_to_process:
                return True
            return super(SaleOrder, orders_to_process).action_quotation_sent()
        return super().action_quotation_sent()

    def action_confirm(self):
        """
        Prevent automatic confirmation of website sale orders during payment
        transaction post-processing and on-site pickup flows.
        Manual confirmation from backend still works.
        """
        if (
            self.env.context.get('from_payment_post_process')
            or self.env.user._is_public()
            or self.env.context.get('send_email')
        ):
            orders_to_process = self.filtered(lambda so: not so.website_id)
            if not orders_to_process:
                return True
            return super(SaleOrder, orders_to_process).action_confirm()
        return super().action_confirm()

    def _append_customer_note_to_terms(self, customer_note):
        """
        Ensure Terms & Conditions stay intact and customer's special
        instruction is appended below them (not replacing them).
        """
        self.ensure_one()
        # Get the company's default T&C (this is what Odoo pre-fills on note)
        default_terms = self.company_id.sale_note or ''

        if not customer_note:
            # No customer note → keep default T&C
            new_note = default_terms
        else:
            # Both → T&C first, then customer's special instruction
            if default_terms:
                new_note = (
                    f"{default_terms}\n\n"
                    f"────────────────────────\n"
                    f"Customer Special Instructions:\n"
                    f"{customer_note}"
                )
            else:
                new_note = f"Customer Special Instructions:\n{customer_note}"

        self.sudo().write({'note': new_note})
