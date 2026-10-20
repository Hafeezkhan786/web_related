from odoo.upgrade.util.orm import env

_AUTOMATION_XMLID = "studio_customization.update_reference_2703a5df-0b3b-443c-ab21-1dc73feaa42d"


def migrate(cr, version):
    # Update the compute (server action `value`, evaluation_type='equation') on the
    # automation's Update Record action.
    automation = env(cr).ref(_AUTOMATION_XMLID)
    automation.action_server_ids.value = "(record.partner_id.phone or '') + '/' + (record.partner_id.custom_mobile or '')"  # fmt:skip
