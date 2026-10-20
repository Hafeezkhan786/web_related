from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@classmethod
def _default_env_context(cls):
    # HACK: TestPointOfSaleHttpCommon.default_env_context seeds the environment context
    # used when the POS session is opened in the browser-based test runner. Our module
    # blocks POS orders that would go negative unless is_negative_pos_allowed is set.
    # Injecting default_is_negative_pos_allowed=True here prevents the block from
    # firing inside the JS/HTTP test environment where per-product flags are not visible.
    return {**super(TestPointOfSaleHttpCommon, cls).default_env_context(), "default_is_negative_pos_allowed": True}


TestPointOfSaleHttpCommon.default_env_context = _default_env_context


_original_setUpClass = TestPointOfSaleHttpCommon.setUpClass.__func__


@classmethod
def custom_setUpClass(cls):
    # HACK: TestPointOfSaleHttpCommon is the shared base for all POS frontend test suites.
    # Many upstream POS tests sell products without caring about stock levels, which can
    # drive quantities negative and trigger our block-negative constraint. Setting
    # is_negative_pos_allowed=True on every product and as an ir.default exempts the
    # entire test suite from the constraint so upstream POS logic runs unmodified.
    # This applies to both at-install and post-install test runs.
    _original_setUpClass(cls)
    cls.env["product.template"].search([]).write({"is_negative_pos_allowed": True})
    cls.env["product.product"].search([]).write({"is_negative_pos_allowed": True})

    cls.env["ir.default"].sudo().set("product.template", "is_negative_pos_allowed", True)
    cls.env["ir.default"].sudo().set("product.product", "is_negative_pos_allowed", True)


TestPointOfSaleHttpCommon.setUpClass = custom_setUpClass
