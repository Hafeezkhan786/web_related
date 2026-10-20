from odoo import fields, models


class MedicinePackagingType(models.Model):
    _name = 'medicine.packaging.type'
    _description = 'Medicine Packaging Type'

    name = fields.Char(required=True)
