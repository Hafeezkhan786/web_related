import re

from markupsafe import Markup

from odoo.fields import Domain
from odoo.upgrade.util.orm import env, recompute_fields

MODEL = "stock.warehouse.orderpoint"
FIELD = "x_studio_vendor"
VIEW_XMLID = "studio_customization.odoo_studio_stock_wa_2efd6238-283c-489c-b67c-92a9d9692d52"

DEPENDS = ("supplier_id, supplier_id.partner_id, product_tmpl_id.seller_ids.sequence, product_tmpl_id.seller_ids.partner_id")  # fmt:skip
COMPUTE = (
    "for record in self: record['%s'] = "
    "record.supplier_id.partner_id or "
    "record.product_tmpl_id.seller_ids.sorted('sequence')[:1].partner_id" % FIELD
)


def _scrub_from_announcement(cr, view_name):
    """Remove the <li> entry for `view_name` from the previously-posted
    `Disabled views` migration announcement, and trace the action in ir.logging."""
    domain = Domain("body", "ilike", "Disabled views") & Domain("body", "ilike", view_name)
    msg = env(cr)["mail.message"].search(domain, limit=1)
    pattern = re.compile(rf"<li>\s*<a[^>]*>\s*{re.escape(view_name)}\s*</a>\s*</li>", re.S)
    msg.body = Markup(pattern.sub("", msg.body))
    env(cr)["ir.logging"].create({
        "name": "Scrubbed Views",
        "type": "server",
        "level": "INFO",
        "message": f"Scrubbed view {view_name!r} from migration announcement",
        "path": __name__,
        "func": "_scrub_from_announcement",
        "line": "0",
    })


def migrate(cr, version):
    IMF = env(cr)["ir.model.fields"]

    IMF.create({
        "name": FIELD,
        "field_description": "Vendor",
        "model_id": env(cr)["ir.model"]._get_id(MODEL),
        "ttype": "many2one",
        "relation": "res.partner",
        "state": "manual",
        "store": True,
        "readonly": True,
        "on_delete": "set null",
        "depends": DEPENDS,
        "compute": COMPUTE,
    })

    recompute_fields(cr, MODEL, [FIELD])

    # Re-enable the Studio view auto-disabled during the upgrade — it referenced
    # x_studio_vendor before this script recreated the field, and scrub it from
    # the "Disabled views" migration announcement.
    view = env(cr).ref(VIEW_XMLID)
    view.active = True
    _scrub_from_announcement(cr, view.name)
