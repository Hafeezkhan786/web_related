from odoo.upgrade.util.orm import env

_LINE_CODES = ["SAL_ST_22", "SAL_ST_25"]


def migrate(cr, version):
    # Odoo 19 reworked tax tags, which exposed a misconfiguration in these custom
    # tags: their amounts now aggregate as negative on the tax report. Prepending '-'
    # to the tax_tags formula negates the expression, flipping the sign back so the
    # reported value is correct. The tag name is unchanged, so the same tags are used.
    lines = env(cr)["account.report.line"].search([("code", "in", _LINE_CODES)])
    for expr in lines.expression_ids:
        expr.formula = f"-{expr.formula}"
