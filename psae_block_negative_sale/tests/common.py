from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_original_get_default_groups = AccountTestInvoicingCommon.get_default_groups.__func__


@classmethod
def _account_custom_get_default_groups(cls):
    # HACK: AccountTestInvoicingCommon.get_default_groups controls which security groups
    # are granted to test users. Our module introduces group_allow_negative_sale, which
    # gates the ability to confirm sales orders that would drive stock negative.
    # Upstream account tests create users without this group, causing our constraint to
    # block their flows. Injecting the group here ensures all inherited test suites
    # (TestSaleCommon, TestSaleOrder, etc.) run with the permission pre-granted so
    # upstream logic is unaffected.
    groups = _original_get_default_groups(cls)
    return groups | cls.env.ref("psae_block_negative_sale.group_allow_negative_sale")


AccountTestInvoicingCommon.get_default_groups = _account_custom_get_default_groups
