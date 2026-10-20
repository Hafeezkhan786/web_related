from odoo.fields import Command

from odoo.addons.sale_stock.tests.test_sale_stock import TestSaleStock


def test_multicompany_transit_with_one_company_for_user(self):
    # HACK: The upstream test creates user_a with only group_sale_salesman, then
    # confirms a sale order on behalf of that user. Our module gates SO confirmation
    # behind group_allow_negative_sale when stock would go negative, which causes
    # the upstream flow to raise an access error even though the test has nothing
    # to do with negative-stock behaviour. We inject group_allow_negative_sale into
    # user_a's groups so the test can confirm the order and assert the inter-company
    # routing logic it was actually written to verify.
    company_a = self.env["res.company"].create({"name": "Company A"})
    company_b = self.env["res.company"].create({"name": "Company B"})
    user_a = self.env["res.users"].create({
        "name": "user only in company a",
        "login": "user a",
        "company_id": company_a.id,
        "company_ids": [Command.link(company_a.id)],
        "group_ids": [
            Command.link(self.env.ref("sales_team.group_sale_salesman").id),
            # start region
            Command.link(self.env.ref("psae_block_negative_sale.group_allow_negative_sale").id),
            # end region
        ],
    })
    product = self.new_product
    so = (
        self
        .env["sale.order"]
        .with_user(user_a)
        .create({
            "partner_id": company_b.partner_id.id,
            "order_line": [
                Command.create({
                    "product_id": product.id,
                }),
            ],
        })
    )
    so.action_confirm()
    intercom_location = self.env.ref("stock.stock_location_inter_company")
    self.assertEqual(so.picking_ids.location_dest_id, intercom_location)
    self.assertEqual(so.picking_ids.move_ids.location_dest_id, intercom_location)


TestSaleStock.test_multicompany_transit_with_one_company_for_user = test_multicompany_transit_with_one_company_for_user
