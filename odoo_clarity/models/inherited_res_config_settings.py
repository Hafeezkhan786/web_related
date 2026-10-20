from odoo import fields, models, api, _


class InheritedResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    odoo_clarity_tracking_code = fields.Char(
        config_parameter="odoo_clarity.odoo_clarity_tracking_code",
        string="Tracking Code",
        copy=True,
        default="",
        store=True,
    )
