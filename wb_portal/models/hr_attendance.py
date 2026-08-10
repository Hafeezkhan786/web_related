# -*- coding: utf-8 -*-
"""Geolocation support for portal check-in / check-out (Odoo 18)."""
from odoo import api, fields, models


class HrAttendance(models.Model):
    """Extend hr.attendance with portal check-in metadata and geo audit info."""
    _inherit = 'hr.attendance'

    work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location',
        tracking=True,
        help='Work location used for the check-in / check-out.')
    geo_verified = fields.Boolean(
        string='Location Verified',
        help='True when the check-in/check-out passed the configured '
             'geolocation radius check of the work location.')

    in_mode = fields.Selection(selection_add=[('portal', 'Portal')])
    out_mode = fields.Selection(selection_add=[('portal', 'Portal')])


class HrWorkLocation(models.Model):
    """Add geolocation configuration to hr.work.location.

    When ``latitude``, ``longitude`` and a positive ``geo_radius`` are set,
    the portal validates that the employee is physically inside that radius
    before allowing a check-in / check-out. If ``geo_enforced`` is also set,
    a location fix is mandatory (the check is refused without coordinates).
    """
    _inherit = 'hr.work.location'

    latitude = fields.Float(
        string='Latitude', digits=(10, 7),
        help='GPS latitude of the work location, e.g. 24.860735 (Karachi).')
    longitude = fields.Float(
        string='Longitude', digits=(10, 7),
        help='GPS longitude of the work location, e.g. 67.001137 (Karachi).')
    geo_radius = fields.Float(
        string='Allowed Radius (km)', default=0.5,
        help='Maximum distance, in kilometers, the employee may be from the '
             'location when checking in/out through the portal.')
    geo_enforced = fields.Boolean(
        string='Require Location Check',
        help='When enabled, portal check-in/check-out is refused if the '
             'employee location cannot be obtained or is outside the radius.')
    geo_configured = fields.Boolean(
        string='Geo Configured', compute='_compute_geo_configured',
        help='Technical: whether enough data is configured to run a radius check.')
    geo_map_url = fields.Char(
        string='Map', compute='_compute_geo_map_url',
        help='Quick link to open the location on Google Maps.')

    @api.depends('latitude', 'longitude', 'geo_radius')
    def _compute_geo_configured(self):
        for location in self:
            location.geo_configured = bool(
                location.latitude and location.longitude
                and (location.geo_radius or 0) > 0)

    @api.depends('latitude', 'longitude')
    def _compute_geo_map_url(self):
        for location in self:
            if location.latitude and location.longitude:
                location.geo_map_url = 'https://maps.google.com?q=%s,%s' % (
                    location.latitude, location.longitude)
            else:
                location.geo_map_url = False


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_report_base_filename(self):
        self.ensure_one()
        return f"Payslip_{self.number or self.id}"