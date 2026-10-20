import re

from markupsafe import Markup

from odoo.fields import Domain
from odoo.upgrade.util.orm import env
from odoo.upgrade.util.records import edit_view

_PRODUCT_LIST_1_XMLID = "studio_customization.odoo_studio_product__80c89475-84e7-49fd-85de-eb5f854fe8ba"
_PRODUCT_LIST_2_XMLID = "studio_customization.odoo_studio_product__25ee0b37-7dc5-40c0-83a4-dc8f7556d6b4"
_PARTNER_FORM_XMLID = "studio_customization.odoo_studio_res_part_f6c928fc-173d-4ccc-a569-ecdf967ef1ac"
_PRODUCT_TEMPLATE_FORM_XMLID = "studio_customization.odoo_studio_product__0bb30b21-47bd-44ba-9fc0-abca51412d9e"
_EMPLOYEE_FORM_VIEW_NAME = "inherited_view_employee_form"


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
    # 1. Deactivate the website-specific (COWed) copy of website_sale.address so the
    #    generic upgraded template applies again — deleting it trips the inherit_id FK
    #    of its own COWed children, archiving sidesteps that and stays reversible.
    env(cr)["ir.ui.view"].search([("key", "=", "website_sale.address"), ("website_id", "!=", False)]).action_archive()

    # 2. website_sale.product_tags COW copy still references the old visible_on_ecommerce
    #    field name in its t-if (SA renamed the field but doesn't touch free-form t-*
    #    expressions, and COW copies aren't overwritten). Retarget it.
    cow = env(cr)["ir.ui.view"].search([("key", "=", "website_sale.product_tags"), ("website_id", "!=", False)])
    with edit_view(cr, view_id=cow.id) as arch:
        node = arch.find(".//t[@t-if='tag.visible_on_ecommerce']")
        node.set("t-if", "tag.visible_to_customers")

    # 3. Product list Studio view: drop allow_negative_sale, rename allow_negative_pos
    #    to is_negative_pos_allowed (on the position="after" xpath, not the attributes
    #    one above it), and remove the obsolete uom_po_id xpath.
    view_name = env(cr).ref(_PRODUCT_LIST_1_XMLID).name
    with edit_view(cr, _PRODUCT_LIST_1_XMLID) as arch:
        after_xp = arch.xpath("./xpath[@expr=\"//list[1]/field[@name='public_categ_ids'][2]\" and @position='after']")[0]  # fmt:skip
        after_xp.remove(after_xp.find("./field[@name='allow_negative_sale']"))
        after_xp.find("./field[@name='allow_negative_pos']").set("name", "is_negative_pos_allowed")

        uom_xp = arch.find(""".//xpath[@expr="//field[@name='uom_po_id']"]""")
        uom_xp.getparent().remove(uom_xp)
    _scrub_from_announcement(cr, view_name)

    # 4. Product list Studio view: remove the obsolete uom_po_id xpath.
    view_name = env(cr).ref(_PRODUCT_LIST_2_XMLID).name
    with edit_view(cr, _PRODUCT_LIST_2_XMLID) as arch:
        uom_xp = arch.find(""".//xpath[@expr="//field[@name='uom_id']"]""")
        uom_xp.getparent().remove(uom_xp)
    _scrub_from_announcement(cr, view_name)

    # 5. inherited_view_employee_form was removed from the system but lingers in the
    #    announcement — scrub it (no xmlid to resolve).
    _scrub_from_announcement(cr, _EMPLOYEE_FORM_VIEW_NAME)

    # 6. Partner form Studio view: drop the phone/mobile label-relabel xpaths. v19
    #    restructured the contact header (phone moved into the header, mobile removed),
    #    so the positional label[1]/label[2] under group[2] no longer target phone/mobile
    #    — left in place they'd relabel the wrong fields or break the view.
    view_name = env(cr).ref(_PARTNER_FORM_XMLID).name
    with edit_view(cr, _PARTNER_FORM_XMLID) as arch:
        for expr in ("//form[1]/sheet[1]/group[1]/group[2]/label[1]", "//form[1]/sheet[1]/group[1]/group[2]/label[2]"):
            node = arch.find(f""".//xpath[@expr="{expr}"]""")
            node.getparent().remove(node)
    _scrub_from_announcement(cr, view_name)

    # 7. Product Template form Studio view: drop the seller_ids inline-list
    #    xpath, now handled by a product.supplierinfo module override.
    view_name = env(cr).ref(_PRODUCT_TEMPLATE_FORM_XMLID).name
    with edit_view(cr, _PRODUCT_TEMPLATE_FORM_XMLID) as arch:
        for seller_xp in arch.xpath(".//xpath[contains(@expr, 'seller_ids')]"):
            seller_xp.getparent().remove(seller_xp)
    _scrub_from_announcement(cr, view_name)
