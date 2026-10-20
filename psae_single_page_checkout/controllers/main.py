import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class SinglePageCheckoutController(WebsiteSale):

    # ════════════════════════════════════════════════════════════════════════
    # 🔒 SAFETY HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _force_order_draft(self, order_sudo, reason=''):
        """Order ko Quotation (draft) mein rakho, LEKIN agar order confirm ('sale', 'done', 'cancel') ho chuka hai to mat badlo."""
        try:
            if (
                order_sudo
                and order_sudo.state not in ('sale', 'done', 'cancel')
                and order_sudo.state != 'draft'
            ):
                order_sudo.sudo().with_context(
                    tracking_disable=True,
                    mail_notrack=True,
                    no_recompute=True,
                ).write({'state': 'draft'})
                _logger.info(
                    "🔒 Order %s forced to DRAFT. Reason: %s",
                    order_sudo.name,
                    reason or 'Safety lock',
                )
        except Exception as e:
            _logger.error(
                "❌ Failed to force order to draft: %s", e, exc_info=True
            )

    def _force_tx_pending(self, tx_sudo, reason=''):
        """Transaction ko hamesha pending mein rakho."""
        try:
            if tx_sudo and tx_sudo.state not in ('pending', 'cancel', 'error'):
                tx_sudo.sudo().write({
                    'state': 'pending',
                    'state_message': _(
                        'Awaiting manual confirmation by sales team.'
                    ),
                })
                _logger.info(
                    "🔒 Transaction %s forced to PENDING. Reason: %s",
                    tx_sudo.reference,
                    reason or 'Safety lock',
                )
        except Exception as e:
            _logger.error(
                "❌ Failed to force tx to pending: %s", e, exc_info=True
            )

    # ════════════════════════════════════════════════════════════════════════
    # Payment Badge Helper
    # ════════════════════════════════════════════════════════════════════════

    def _get_payment_badge_info(self, name, code):
        """Helper to return badge styling and icon based on payment name/code."""
        name_lower = (name or '').lower()
        code_lower = (code or '').lower()

        if (
            'cod' in name_lower or 'cod' in code_lower
            or 'site' in name_lower or 'site' in code_lower
            or 'cash' in name_lower
        ):
            return {
                'text': 'COD',
                'class': 'option-badge',
                'icon': 'oi oi-box me-1',
            }
        elif (
            'card' in name_lower or 'visa' in name_lower
            or 'master' in name_lower or 'card' in code_lower
        ):
            return {
                'text': 'VISA / MC',
                'class': 'option-badge text-primary',
                'icon': '',
            }
        elif 'easypaisa' in name_lower or 'easypaisa' in code_lower:
            return {
                'text': 'EasyPaisa',
                'class': 'option-badge text-success',
                'icon': '',
            }
        elif 'jazzcash' in name_lower or 'jazzcash' in code_lower:
            return {
                'text': 'JazzCash',
                'class': 'option-badge text-danger',
                'icon': '',
            }
        elif (
            'bank' in name_lower or 'transfer' in name_lower
            or 'wire' in name_lower or 'raast' in name_lower
            or 'payfast' in name_lower or 'bank' in code_lower
            or 'transfer' in code_lower or 'wire' in code_lower
        ):
            return {
                'text': name,
                'class': 'option-badge text-info',
                'icon': 'fa fa-university me-1',
            }
        else:
            return {'text': name, 'class': 'option-badge', 'icon': ''}

    # ════════════════════════════════════════════════════════════════════════
    # Carrier Helpers
    # ════════════════════════════════════════════════════════════════════════

    def _is_pickup_in_store(self, carrier):
        """Return True if carrier is a Pick up in Store type."""
        if not carrier:
            return False
        carrier_name_lower = (carrier.name or '').strip().lower()
        is_pickup = (
            'pick up in store' in carrier_name_lower
            or 'pickup in store' in carrier_name_lower
            or 'pick-up in store' in carrier_name_lower
        )
        if hasattr(carrier, 'delivery_type') and carrier.delivery_type == 'pick_up_in_store':
            is_pickup = True
        return is_pickup

    def _is_carrier_compatible(self, carrier, partner_state):
        if not partner_state:
            return True

        state_name_lower = (partner_state.name or '').lower()
        is_karachi = 'karachi' in state_name_lower or 'sindh' in state_name_lower

        if self._is_pickup_in_store(carrier):
            if getattr(carrier, 'state_ids', None):
                return partner_state.id in carrier.state_ids.ids
            return is_karachi

        if getattr(carrier, 'state_ids', None):
            if partner_state.id not in carrier.state_ids.ids:
                return False

        carrier_name_lower = (carrier.name or '').lower()
        if ('karachi' in carrier_name_lower) and not is_karachi:
            return False
        if (
            ('other provinces' in carrier_name_lower
             or 'outside karachi' in carrier_name_lower)
            and is_karachi
        ):
            return False

        return True

    # ════════════════════════════════════════════════════════════════════════
    # Payment Type Helpers
    # ════════════════════════════════════════════════════════════════════════

    def _is_bank_transfer(self, opt):
        """Check if a payment option is a bank transfer type."""
        name = (opt.get('name') or '').lower()
        code = (opt.get('code') or '').lower()
        custom_mode = (opt.get('custom_mode') or '').lower()
        provider_code = (opt.get('provider_code') or '').lower()

        return (
            'bank' in name
            or 'transfer' in name
            or 'wire' in name
            or 'raast' in name
            or 'payfast' in name
            or 'bank' in code
            or 'transfer' in code
            or 'wire' in code
            or provider_code == 'wire_transfer'
            or 'wire' in provider_code
            or 'bank' in provider_code
            or 'bank' in custom_mode
            or 'transfer' in custom_mode
            or 'wire' in custom_mode
            or (
                code == 'custom' and (
                    'bank' in custom_mode
                    or 'transfer' in custom_mode
                    or 'wire' in custom_mode
                )
            )
        )

    def _is_cod_or_site(self, opt):
        """Check if a payment option is COD or Pay on Site type."""
        name = (opt.get('name') or '').lower()
        code = (opt.get('code') or '').lower()
        custom_mode = (opt.get('custom_mode') or '').lower()

        return (
            'cod' in name
            or 'cod' in code
            or 'cod' in custom_mode
            or 'cash on delivery' in name
            or 'cash' in name
            or 'pay on site' in name
            or 'pay_on_site' in custom_mode
            or 'site' in name
            or 'site' in custom_mode
        )

    def _is_cod_only(self, opt):
        """Return True only for Cash on Delivery."""
        name = (opt.get('name') or '').strip().lower()
        code = (opt.get('code') or '').strip().lower()
        custom_mode = (opt.get('custom_mode') or '').strip().lower()
        provider_code = (opt.get('provider_code') or '').strip().lower()

        if self._is_pay_on_site(opt):
            return False

        return (
            'cash on delivery' in name
            or name == 'cod'
            or 'cod' in name
            or code == 'cod'
            or 'cod' in code
            or custom_mode == 'cod'
            or 'cod' in custom_mode
            or provider_code == 'cod'
            or 'cod' in provider_code
            or ('cash' in name and 'delivery' in name)
        )

    def _is_pay_on_site(self, opt):
        """Return True only for the Pay on Site payment provider."""
        name = (opt.get('name') or '').strip().lower()
        code = (opt.get('code') or '').strip().lower()
        custom_mode = (opt.get('custom_mode') or '').strip().lower()
        provider_code = (opt.get('provider_code') or '').strip().lower()

        return (
            name == 'pay on site'
            or name == 'pay_on_site'
            or custom_mode == 'pay on site'
            or custom_mode == 'pay_on_site'
            or code == 'pay_on_site'
            or provider_code == 'pay_on_site'
            or 'pay on site' in name
            or 'pay_on_site' in name
            or 'pay on site' in custom_mode
            or 'pay_on_site' in custom_mode
        )

    def _filter_payments_by_carrier(self, payment_options, carrier):
        """
        Payment rules:
        1. Pick up in store              → ONLY Pay on Site
        2. Courier Charges (Sindh)       → ONLY Bank Transfer
        3. Other Areas / Karachi Only    → Bank Transfer + COD (NO Pay on Site)
        4. All others                    → All EXCEPT Pay on Site
        """
        if not carrier:
            return [
                opt for opt in payment_options
                if not self._is_pay_on_site(opt)
            ]

        carrier_name_lower = (carrier.name or '').strip().lower()

        _logger.info(
            "🔍 PAYMENT FILTER | Carrier='%s' | All methods=%s",
            carrier.name,
            [opt.get('name') for opt in payment_options],
        )

        # Rule 1
        if self._is_pickup_in_store(carrier):
            filtered = [
                opt for opt in payment_options
                if self._is_pay_on_site(opt)
            ]
            _logger.info(
                "🎯 Pickup in Store → ONLY Pay on Site. Allowed=%s",
                [opt.get('name') for opt in filtered],
            )
            return filtered

        # Rule 2
        if 'courier charges' in carrier_name_lower and 'sindh' in carrier_name_lower:
            filtered = [
                opt for opt in payment_options
                if self._is_bank_transfer(opt)
            ]
            _logger.info(
                "🎯 Courier Charges (Sindh) → ONLY Bank Transfer. Allowed=%s",
                [opt.get('name') for opt in filtered],
            )
            return filtered

        # Rule 3
        if 'other areas' in carrier_name_lower or 'karachi only' in carrier_name_lower:
            filtered = [
                opt for opt in payment_options
                if (self._is_bank_transfer(opt) or self._is_cod_only(opt))
                and not self._is_pay_on_site(opt)
            ]
            _logger.info(
                "🎯 Other Areas/Karachi Only → Bank Transfer + COD. Allowed=%s",
                [opt.get('name') for opt in filtered],
            )
            return filtered

        # Rule 4
        filtered = [
            opt for opt in payment_options
            if not self._is_pay_on_site(opt)
        ]
        _logger.info(
            "ℹ️ Normal delivery '%s' → all except Pay on Site. Allowed=%s",
            carrier.name,
            [opt.get('name') for opt in filtered],
        )
        return filtered

    # ════════════════════════════════════════════════════════════════════════
    # Checkout Page Values
    # ════════════════════════════════════════════════════════════════════════

    def _prepare_checkout_page_values(self, order_sudo, **kwargs):
        partner_sudo = order_sudo.partner_id
        values = {
            'order': order_sudo,
            'website_sale_order': order_sudo,
            'use_delivery_as_billing': (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            ),
            'only_services': order_sudo.only_services,
            'address_url': '/shop/address',
        }
        if not request.env.user._is_public():
            values.update(self._prepare_address_data(partner_sudo, **kwargs))
        return values

    def _get_checkout_options_data(self, order_sudo, **query_params):
        partner_sudo = order_sudo.partner_shipping_id or order_sudo.partner_id

        # Guest state / country detection
        guest_state = None
        guest_country_id = None

        if request.env.user._is_public():
            guest_state_id = request.session.get('guest_state_id')
            session_country_id = request.session.get('guest_country_id')

            if guest_state_id:
                guest_state = request.env['res.country.state'].sudo().browse(
                    int(guest_state_id)
                )
            if session_country_id:
                guest_country_id = int(session_country_id)

            public_partner = self._get_public_partner()
            if (
                not guest_state and partner_sudo
                and partner_sudo.id != public_partner.id
                and partner_sudo.state_id
            ):
                guest_state = partner_sudo.state_id
            if not guest_country_id and partner_sudo and partner_sudo.country_id:
                guest_country_id = partner_sudo.country_id.id

        filter_state = guest_state if guest_state else (
            partner_sudo.state_id if partner_sudo else None
        )
        filter_country = guest_country_id if guest_country_id else (
            partner_sudo.country_id.id
            if partner_sudo and partner_sudo.country_id else None
        )

        _logger.info(
            "CHECKOUT FILTER: filter_state=%s (id=%s), filter_country=%s",
            filter_state.name if filter_state else None,
            filter_state.id if filter_state else None,
            filter_country,
        )

        # Delivery methods
        available_dms = request.env['delivery.carrier'].sudo().search([
            ('website_published', '=', True),
        ])

        if filter_state:
            def carrier_matches_state(c):
                if self._is_pickup_in_store(c):
                    if c.state_ids:
                        return filter_state.id in c.state_ids.ids
                    state_name_lower = (filter_state.name or '').lower()
                    return 'sindh' in state_name_lower or 'karachi' in state_name_lower
                if c.state_ids:
                    return filter_state.id in c.state_ids.ids
                return True

            available_dms = available_dms.filtered(carrier_matches_state)
            _logger.info(
                "Carriers after state filter: %s",
                available_dms.mapped('name'),
            )
        else:
            available_dms = available_dms.filtered(
                lambda c: not self._is_pickup_in_store(c)
            )
            _logger.info(
                "No state → Pickup hidden. Carriers=%s",
                available_dms.mapped('name'),
            )

        if filter_country:
            available_dms = available_dms.filtered(
                lambda c: not c.country_ids or filter_country in c.country_ids.ids
            )

        if order_sudo.carrier_id and order_sudo.carrier_id not in available_dms:
            order_sudo._remove_delivery_line()

        order_sudo._recompute_cart()

        # 🔒 Safety
        self._force_order_draft(order_sudo, reason='After _recompute_cart')

        currency = order_sudo.currency_id

        # Build dms_data
        dms_data = []
        for dm in available_dms:
            price = 0.0
            if hasattr(dm, 'fixed_price'):
                price = dm.fixed_price
            try:
                rate_res = dm.rate_shipment(order_sudo)
                if rate_res.get('success') and 'price' in rate_res:
                    price = rate_res['price']
            except Exception:
                pass

            price_formatted = (
                "Rs. 0" if price == 0
                else f"{currency.symbol} {price:.2f}"
            )
            dms_data.append({
                'id': dm.id,
                'name': dm.name,
                'price': price,
                'price_formatted': price_formatted,
                'is_selected': bool(
                    order_sudo.carrier_id and order_sudo.carrier_id.id == dm.id
                ),
            })

        # Payment providers
        payment_values = self._get_shop_payment_values(order_sudo, **query_params)

        # 🔒 Safety
        self._force_order_draft(
            order_sudo, reason='After _get_shop_payment_values'
        )

        provider_domain = [
            '|',
            ('state', 'in', ['enabled', 'test']),
            ('is_published', '=', True),
            ('company_id', '=', order_sudo.company_id.id),
        ]
        providers_sudo = request.env['payment.provider'].sudo().search(provider_domain)

        website = request.website
        if website:
            providers_sudo = providers_sudo.filtered(
                lambda p: not p.website_id or p.website_id.id == website.id
            )

        payment_methods_sudo = (
            payment_values.get('payment_methods_sudo')
            or request.env['payment.method'].sudo()
        )

        if filter_state:
            st_id = filter_state.id

            def provider_matches_state(p):
                if p.available_state_ids:
                    return st_id in p.available_state_ids.ids
                return True

            providers_sudo = providers_sudo.filtered(provider_matches_state)

            if payment_methods_sudo:
                payment_methods_sudo = payment_methods_sudo.filtered(
                    lambda pm: any(p in providers_sudo for p in pm.provider_ids)
                )

        if filter_country:
            def provider_matches_country(p):
                if hasattr(p, 'available_country_ids') and p.available_country_ids:
                    return filter_country in p.available_country_ids.ids
                return True

            providers_sudo = providers_sudo.filtered(provider_matches_country)

        # Build payment options
        payment_options = []
        seen_provider_ids = set()

        for provider in providers_sudo:
            if provider.id in seen_provider_ids:
                continue
            seen_provider_ids.add(provider.id)

            custom_mode_val = ''
            if hasattr(provider, 'custom_mode') and provider.custom_mode:
                custom_mode_val = str(provider.custom_mode)

            matching_pm = False
            if payment_methods_sudo:
                for pm in payment_methods_sudo:
                    if provider in pm.provider_ids:
                        matching_pm = pm
                        break
            if (
                not matching_pm
                and hasattr(provider, 'payment_method_ids')
                and provider.payment_method_ids
            ):
                matching_pm = provider.payment_method_ids[0]
            if not matching_pm:
                matching_pm = request.env['payment.method'].sudo().search(
                    [('provider_ids', 'in', [provider.id])], limit=1
                ) or request.env['payment.method'].sudo().search([], limit=1)

            badge_source_code = custom_mode_val or provider.code or ''
            badge = self._get_payment_badge_info(provider.name, badge_source_code)

            option = {
                'id': provider.id,
                'type': 'provider',
                'name': provider.name,
                'code': provider.code or '',
                'provider_id': provider.id,
                'provider_code': provider.code or '',
                'custom_mode': custom_mode_val,
                'payment_method_id': matching_pm.id if matching_pm else False,
                'badge_text': badge['text'],
                'badge_class': badge['class'],
                'badge_icon': badge.get('icon', ''),
                'pending_msg': provider.pending_msg or '',
            }
            payment_options.append(option)

        if order_sudo.carrier_id:
            payment_options = self._filter_payments_by_carrier(
                payment_options,
                order_sudo.carrier_id,
            )

        _logger.info(
            "✅ FINAL payment_options count=%s: %s",
            len(payment_options),
            [o['name'] for o in payment_options],
        )

        return {
            'available_dms': available_dms,
            'dms_data': dms_data,
            'payment_values': payment_values,
            'payment_options': payment_options,
            'amount_delivery_formatted': f"{currency.symbol} {order_sudo.amount_delivery:.2f}",
            'amount_untaxed_formatted': f"{currency.symbol} {order_sudo.amount_untaxed:.2f}",
            'amount_tax_formatted': f"{currency.symbol} {order_sudo.amount_tax:.2f}",
            'amount_total_formatted': f"{currency.symbol} {order_sudo.amount_total:.2f}",
        }

    # ════════════════════════════════════════════════════════════════════════
    # Routes
    # ════════════════════════════════════════════════════════════════════════

    @http.route('/shop/address', type='http', auth='public', website=True, sitemap=False)
    def shop_address(self, **post):
        return request.redirect('/shop/checkout')

    @http.route(
        '/shop/checkout',
        type='http',
        methods=['GET', 'POST'],
        auth='public',
        website=True,
        sitemap=False,
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        order_sudo = request.cart
        if not order_sudo or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        request.session['sale_last_order_id'] = order_sudo.id

        if redirection := self._check_cart(order_sudo):
            return redirection

        order_sudo._recompute_cart()
        self._force_order_draft(order_sudo, reason='shop_checkout page load')

        checkout_page_values = self._prepare_checkout_page_values(
            order_sudo, **query_params
        )
        options_data = self._get_checkout_options_data(order_sudo, **query_params)

        checkout_page_values['delivery_methods'] = options_data['available_dms']
        checkout_page_values['payment_options'] = options_data['payment_options']
        checkout_page_values.update(options_data['payment_values'])

        partner_sudo = order_sudo.partner_shipping_id or order_sudo.partner_id
        pakistan = request.env['res.country'].sudo().search(
            [('code', '=', 'PK')], limit=1
        )
        states = request.env['res.country.state'].sudo().search(
            [('country_id', '=', pakistan.id)]
        )

        public_partner = self._get_public_partner()
        if partner_sudo.id == public_partner.id:
            partner_for_display = request.env['res.partner'].sudo().new({
                'name': '',
                'phone': '',
                'email': '',
                'street': '',
                'city': '',
                'state_id': False,
                'country_id': False,
                'custom_mobile': '',
                'zip': '',
            })
        else:
            partner_for_display = partner_sudo

        checkout_page_values.update({
            'order': order_sudo,
            'partner': partner_for_display,
            'countries': pakistan,
            'states': states,
            'default_country_id': partner_for_display.country_id.id or 174,
        })

        return request.render(
            'psae_single_page_checkout.single_checkout',
            checkout_page_values,
        )

    @http.route(
        '/shop/single_checkout/update_delivery',
        type='json',
        auth='public',
        website=True,
    )
    def update_single_checkout_delivery(self, carrier_id, **kwargs):
        order_sudo = request.cart
        if not order_sudo:
            return {'error': _('No active cart found.')}

        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
        if not carrier.exists():
            return {'error': _('Selected delivery method is invalid.')}

        try:
            rate = carrier.rate_shipment(order_sudo)
        except Exception as e:
            _logger.error(
                "rate_shipment failed for carrier %s: %s", carrier.name, e
            )
            rate = {
                'success': True,
                'price': carrier.fixed_price,
                'warning_message': False,
            }

        if not rate.get('success') or rate.get('price') is None:
            rate = {
                'success': True,
                'price': carrier.fixed_price,
                'warning_message': False,
            }

        order_sudo._set_delivery_method(carrier, rate=rate)
        order_sudo._recompute_cart()
        order_sudo.invalidate_recordset([
            'amount_delivery', 'amount_total',
            'amount_untaxed', 'amount_tax',
        ])

        self._force_order_draft(order_sudo, reason='After update_delivery')

        currency = order_sudo.currency_id
        options_data = self._get_checkout_options_data(order_sudo)

        _logger.info(
            "DELIVERY UPDATE: carrier='%s', total=%s",
            carrier.name,
            order_sudo.amount_total,
        )

        return {
            'success': True,
            'carrier_id': carrier.id,
            'carrier_name': carrier.name,
            'payment_options': options_data['payment_options'],
            'amount_delivery_formatted': f"{currency.symbol} {order_sudo.amount_delivery:.2f}",
            'amount_untaxed_formatted': f"{currency.symbol} {order_sudo.amount_untaxed:.2f}",
            'amount_tax_formatted': f"{currency.symbol} {order_sudo.amount_tax:.2f}",
            'amount_total_formatted': f"{currency.symbol} {order_sudo.amount_total:.2f}",
            'amount_total': order_sudo.amount_total,
        }

    def _get_default_sale_terms(self, order_sudo):
        """Discover and return the default Terms & Conditions."""
        company = order_sudo.company_id

        if hasattr(company, 'invoice_terms'):
            terms = company.invoice_terms
            if terms:
                return terms

        if company.partner_id and hasattr(company.partner_id, 'sale_note'):
            terms = company.partner_id.sale_note
            if terms:
                return terms

        try:
            default_vals = request.env['sale.order'].sudo().with_company(
                company.id
            ).default_get(['note'])
            terms = default_vals.get('note') or ''
            if terms:
                return terms
        except Exception:
            pass

        return ''

    def _get_public_partner(self):
        return request.website.user_id.sudo().partner_id

    def _get_or_create_guest_partner(self, order_sudo, vals):
        public_partner = self._get_public_partner()
        current_partner = order_sudo.partner_id

        if current_partner.id != public_partner.id:
            return current_partner

        guest_partner = request.env['res.partner'].sudo().create({
            'name': _('Guest Customer'),
            'company_id': order_sudo.company_id.id,
            'type': 'contact',
        })
        order_sudo.sudo().write({
            'partner_invoice_id': guest_partner.id,
            'partner_shipping_id': guest_partner.id,
        })
        return guest_partner

    @http.route(
        '/shop/single_checkout/update_address',
        type='json',
        auth='public',
        website=True,
    )
    def update_single_checkout_address(
        self, name=None, phone=None, email=None, street=None,
        street2=None, city=None, state_id=None, country_id=None,
        mobile=None, zip=None, **kwargs
    ):
        order_sudo = request.cart
        if not order_sudo:
            return {'error': _('No active cart found.')}

        vals = {}
        if name:
            vals['name'] = name.strip() if hasattr(name, 'strip') else name
        if phone:
            vals['phone'] = phone
        if mobile is not None:
            vals['custom_mobile'] = (
                mobile.strip() if hasattr(mobile, 'strip') else mobile
            )
        if email:
            vals['email'] = email
        if street:
            vals['street'] = street
        if street2 is not None:
            vals['street2'] = (
                street2.strip() if hasattr(street2, 'strip') else street2
            )
        if city:
            vals['city'] = city
        if state_id:
            vals['state_id'] = int(state_id)
        if country_id:
            vals['country_id'] = int(country_id)
        if zip:
            vals['zip'] = zip

        if vals:
            if not request.env.user._is_public():
                partner_shipping = order_sudo.partner_shipping_id
                partner_main = order_sudo.partner_id
                if partner_shipping:
                    partner_shipping.sudo().write(vals)
                    partner_shipping.invalidate_recordset([
                        'state_id', 'country_id', 'city',
                        'street', 'street2',
                    ])
                if partner_main and partner_main != partner_shipping:
                    partner_main.sudo().write(vals)
                    partner_main.invalidate_recordset([
                        'state_id', 'country_id', 'city',
                        'street', 'street2',
                    ])
            else:
                self._get_or_create_guest_partner_for_order(order_sudo, vals)
                if state_id:
                    request.session['guest_state_id'] = int(state_id)
                if country_id:
                    request.session['guest_country_id'] = int(country_id)

            client_ref_parts = []
            if phone:
                client_ref_parts.append(phone.strip())
            if mobile:
                client_ref_parts.append(mobile.strip())
            if client_ref_parts:
                order_sudo.sudo().write({
                    'client_order_ref': '/'.join(client_ref_parts)
                })

            order_sudo.invalidate_recordset()

        self._force_order_draft(order_sudo, reason='After update_address')

        options_data = self._get_checkout_options_data(order_sudo)

        return {
            'success': True,
            'partner_id': (
                order_sudo.partner_shipping_id or order_sudo.partner_id
            ).id,
            'delivery_methods': options_data['dms_data'],
            'payment_options': options_data['payment_options'],
            'carrier_id': order_sudo.carrier_id.id if order_sudo.carrier_id else False,
            'amount_delivery_formatted': options_data['amount_delivery_formatted'],
            'amount_untaxed_formatted': options_data['amount_untaxed_formatted'],
            'amount_tax_formatted': options_data['amount_tax_formatted'],
            'amount_total_formatted': options_data['amount_total_formatted'],
        }

    def _get_or_create_guest_partner_for_order(self, order_sudo, vals):
        public_partner = self._get_public_partner()
        current_partner = order_sudo.partner_id

        partner_vals = dict(vals)
        if 'name' not in partner_vals or not partner_vals.get('name'):
            partner_vals['name'] = _('Guest Customer')

        if current_partner.id == public_partner.id:
            partner_vals['company_id'] = order_sudo.company_id.id
            partner_vals['type'] = 'contact'

            guest_partner = request.env['res.partner'].sudo().create(partner_vals)

            order_sudo.sudo().write({
                'partner_id': guest_partner.id,
                'partner_invoice_id': guest_partner.id,
                'partner_shipping_id': guest_partner.id,
            })
            _logger.info(
                "Created guest partner '%s' (id=%s) for order %s",
                guest_partner.name, guest_partner.id, order_sudo.name,
            )
        else:
            guest_partner = current_partner
            guest_partner.sudo().write(vals)
            guest_partner.invalidate_recordset([
                'state_id', 'country_id', 'city', 'street',
                'name', 'phone', 'email',
            ])

        return guest_partner

    @http.route(
        '/shop/single_checkout/get_states',
        type='json',
        auth='public',
        website=True,
    )
    def get_states_by_country(self, country_id, **kwargs):
        try:
            country_id = int(country_id)
            states = request.env['res.country.state'].sudo().search([
                ('country_id', '=', country_id)
            ])
            return {'states': [{'id': s.id, 'name': s.name} for s in states]}
        except (ValueError, TypeError):
            return {'states': []}

    @http.route(
        '/shop/single_checkout/update_notes',
        type='json',
        auth='public',
        website=True,
    )
    def update_single_checkout_notes(self, note, **kwargs):
        """Save order special instructions."""
        order_sudo = request.cart
        if not order_sudo:
            return {'error': _('No active cart found.')}

        default_terms = self._get_default_sale_terms(order_sudo)

        if not note:
            new_note = default_terms
        elif default_terms:
            new_note = (
                f"{default_terms}\n\n"
                f"────────────────────────\n"
                f"Customer Special Instructions:\n"
                f"{note}"
            )
        else:
            new_note = f"Customer Special Instructions:\n{note}"

        order_sudo.sudo().write({'note': new_note})
        self._force_order_draft(order_sudo, reason='After update_notes')

        return {'success': True}

    # ════════════════════════════════════════════════════════════════════════
    # 🔒 MAIN PAYMENT PROCESSING
    # ════════════════════════════════════════════════════════════════════════

    @http.route(
        '/shop/single_checkout/process_payment',
        type='http',
        methods=['POST'],
        auth='public',
        website=True,
        csrf=True,
    )
    def single_checkout_process_payment(
        self, provider_id=None, payment_method_id=None, **post
    ):
        from odoo.fields import Command

        try:
            try:
                if not request.env.cr.closed:
                    request.env.cr.rollback()
            except Exception:
                pass

            order_sudo = request.cart
            if not order_sudo or not order_sudo.order_line:
                return request.redirect('/shop/cart')

            self._force_order_draft(order_sudo, reason='Payment processing start')

            # ── 1. Address Fields ─────────────────────────────────────────
            first_name = (post.get('first_name') or '').strip()
            last_name = (post.get('last_name') or '').strip()
            name = (
                (first_name + ' ' + last_name).strip()
                if (first_name or last_name) else None
            )
            phone = (post.get('phone') or '').strip()
            mobile = (post.get('mobile') or '').strip()
            street = (post.get('street') or '').strip()
            street2 = (post.get('street2') or '').strip()
            city = (post.get('city') or '').strip()
            state_id = post.get('state_id')
            country_id = post.get('country_id')
            email = (post.get('email') or '').strip()
            zip_code = (post.get('zip') or '').strip()

            # Ensure all required fields are present (everything except WhatsApp number & zip)
            if not (first_name and last_name and phone and street and street2 and city and state_id and country_id and email):
                _logger.warning("Checkout attempt with missing required fields.")
                return request.redirect('/shop/checkout')

            vals = {}
            if name:
                vals['name'] = name
            if phone:
                vals['phone'] = phone
            if mobile:
                vals['custom_mobile'] = mobile
            if email:
                vals['email'] = email
            if street:
                vals['street'] = street
            if street2 is not None:
                vals['street2'] = street2
            if city:
                vals['city'] = city
            if state_id:
                try:
                    vals['state_id'] = int(state_id)
                except (ValueError, TypeError):
                    pass
            if country_id:
                try:
                    vals['country_id'] = int(country_id)
                except (ValueError, TypeError):
                    pass
            if zip_code:
                vals['zip'] = zip_code

            # ── 2. Partner Assignment ─────────────────────────────────────
            if not request.env.user._is_public():
                logged_in_partner = request.env.user.partner_id
                if order_sudo.partner_id.id != logged_in_partner.id:
                    order_sudo.sudo().write({
                        'partner_id': logged_in_partner.id,
                        'partner_invoice_id': logged_in_partner.id,
                        'partner_shipping_id': logged_in_partner.id,
                    })
                if vals:
                    partner_shipping = order_sudo.partner_shipping_id
                    partner_main = order_sudo.partner_id
                    if partner_shipping:
                        partner_shipping.sudo().write(vals)
                    if partner_main and partner_main != partner_shipping:
                        partner_main.sudo().write(vals)
            else:
                if not vals.get('name'):
                    _logger.error("Guest checkout attempt without name.")
                    return request.redirect('/shop/checkout')
                if not vals.get('email'):
                    _logger.error("Guest checkout attempt without email.")
                    return request.redirect('/shop/checkout')

                guest_partner = self._get_or_create_guest_partner_for_order(
                    order_sudo, vals
                )
                _logger.info(
                    "Guest order %s → partner '%s' (id=%s)",
                    order_sudo.name, guest_partner.name, guest_partner.id,
                )

            self._force_order_draft(order_sudo, reason='After partner assignment')

            # ── Save phone to client_order_ref ────────────────────────────
            client_ref_parts = []
            if phone:
                client_ref_parts.append(phone.strip())
            if mobile:
                client_ref_parts.append(mobile.strip())
            if client_ref_parts:
                order_sudo.sudo().write({
                    'client_order_ref': '/'.join(client_ref_parts)
                })

            # ── 3. Delivery Carrier ───────────────────────────────────────
            delivery_type = post.get('delivery_type')
            if delivery_type:
                try:
                    carrier = request.env['delivery.carrier'].sudo().browse(
                        int(delivery_type)
                    )
                    if carrier.exists():
                        rate = carrier.rate_shipment(order_sudo)
                        order_sudo._set_delivery_method(carrier, rate=rate)
                        self._force_order_draft(
                            order_sudo,
                            reason='After _set_delivery_method',
                        )
                except Exception as e:
                    _logger.error("Error setting delivery carrier: %s", e)

            # ── 4. Notes ──────────────────────────────────────────────────
            note = post.get('note')
            default_terms = self._get_default_sale_terms(order_sudo)

            if note:
                new_note = (
                    f"{default_terms}\n\n────────────────────────\n"
                    f"Customer Special Instructions:\n{note}"
                    if default_terms
                    else f"Customer Special Instructions:\n{note}"
                )
                order_sudo.sudo().write({'note': new_note})
            elif default_terms and not order_sudo.note:
                order_sudo.sudo().write({'note': default_terms})

            # ── 5. Delivery Partner (child contact) ───────────────────────
            main_partner = order_sudo.partner_id
            delivery_display_name = street or _('Delivery Address')

            delivery_partner_vals = {
                'name': delivery_display_name,
                'type': 'delivery',
                'parent_id': main_partner.id,
                'company_id': order_sudo.company_id.id,
                'phone': phone or '',
                'email': email or '',
                'street': street or '',
                'street2': street2 or '',
                'city': city or '',
                'zip': zip_code or '',
                'active': True,
            }
            if state_id:
                try:
                    delivery_partner_vals['state_id'] = int(state_id)
                except (ValueError, TypeError):
                    pass
            if country_id:
                try:
                    delivery_partner_vals['country_id'] = int(country_id)
                except (ValueError, TypeError):
                    pass

            existing_shipping = order_sudo.partner_shipping_id
            if (
                existing_shipping
                and existing_shipping.id != main_partner.id
                and existing_shipping.type == 'delivery'
            ):
                existing_shipping.sudo().write(delivery_partner_vals)
                existing_shipping.invalidate_recordset(['name', 'display_name'])
                delivery_partner = existing_shipping
            else:
                search_domain = [
                    ('type', '=', 'delivery'),
                    ('parent_id', '=', main_partner.id),
                    ('company_id', '=', order_sudo.company_id.id),
                    '|', ('active', '=', True), ('active', '=', False),
                ]
                candidate = request.env['res.partner']
                if phone:
                    candidate = request.env['res.partner'].sudo().search(
                        search_domain + [('phone', '=', phone)], limit=1
                    )
                if not candidate and street:
                    candidate = request.env['res.partner'].sudo().search(
                        search_domain + [
                            ('street', '=', street),
                            ('city', '=', city or ''),
                        ], limit=1
                    )

                if candidate:
                    candidate.sudo().write(delivery_partner_vals)
                    candidate.invalidate_recordset(
                        ['name', 'display_name', 'active']
                    )
                    delivery_partner = candidate
                else:
                    delivery_partner = request.env['res.partner'].sudo().create(
                        delivery_partner_vals
                    )

            order_sudo.sudo().write({'partner_shipping_id': delivery_partner.id})
            self._force_order_draft(
                order_sudo, reason='After setting partner_shipping_id'
            )

            # ── 6. Billing Partner ────────────────────────────────────────
            billing_same_as_delivery = post.get('billing_same_as_delivery')

            if billing_same_as_delivery:
                previous_billing = order_sudo.partner_invoice_id
                order_sudo.sudo().write({
                    'partner_invoice_id': delivery_partner.id
                })

                if (
                    previous_billing
                    and previous_billing.id != delivery_partner.id
                    and previous_billing.id != main_partner.id
                    and previous_billing.type == 'invoice'
                    and previous_billing.parent_id.id == main_partner.id
                ):
                    other_orders = request.env['sale.order'].sudo().search_count([
                        '|',
                        ('partner_invoice_id', '=', previous_billing.id),
                        ('partner_shipping_id', '=', previous_billing.id),
                        ('id', '!=', order_sudo.id),
                    ])
                    if other_orders == 0:
                        try:
                            previous_billing.sudo().write({'active': False})
                        except Exception as e:
                            _logger.warning(
                                "Could not archive old billing partner: %s", e
                            )
            else:
                billing_first_name = (post.get('billing_first_name') or '').strip()
                billing_last_name = (post.get('billing_last_name') or '').strip()
                billing_name = (
                    billing_first_name + ' ' + billing_last_name
                ).strip()
                billing_phone = (post.get('billing_phone') or '').strip()
                billing_street = (post.get('billing_street') or '').strip()
                billing_street2 = (post.get('billing_street2') or '').strip()
                billing_city = (post.get('billing_city') or '').strip()
                billing_state_id = post.get('billing_state_id')
                billing_country_id = post.get('billing_country_id')
                billing_email = (post.get('billing_email') or '').strip()
                billing_zip = (post.get('billing_zip') or '').strip()

                if not (billing_name and billing_phone and billing_street and billing_street2 and billing_city and billing_state_id and billing_country_id and billing_email):
                    _logger.warning("Billing address missing required fields.")
                    return request.redirect('/shop/checkout')
                else:
                    billing_partner_vals = {
                        'name': billing_street or _('Billing Address'),
                        'type': 'invoice',
                        'parent_id': main_partner.id,
                        'company_id': order_sudo.company_id.id,
                        'phone': billing_phone or phone or '',
                        'email': billing_email or email or '',
                        'street': billing_street or '',
                        'street2': billing_street2 or '',
                        'city': billing_city or '',
                        'zip': billing_zip or '',
                        'active': True,
                    }
                    if billing_state_id:
                        try:
                            billing_partner_vals['state_id'] = int(billing_state_id)
                        except (ValueError, TypeError):
                            pass
                    if billing_country_id:
                        try:
                            billing_partner_vals['country_id'] = int(billing_country_id)
                        except (ValueError, TypeError):
                            pass

                    billing_partner = None
                    existing_billing = order_sudo.partner_invoice_id

                    if (
                        existing_billing
                        and existing_billing.id != main_partner.id
                        and existing_billing.id != delivery_partner.id
                        and existing_billing.type == 'invoice'
                    ):
                        existing_billing.sudo().write(billing_partner_vals)
                        existing_billing.invalidate_recordset(
                            ['name', 'display_name']
                        )
                        billing_partner = existing_billing
                    else:
                        search_domain = [
                            ('type', '=', 'invoice'),
                            ('parent_id', '=', main_partner.id),
                            ('company_id', '=', order_sudo.company_id.id),
                            '|', ('active', '=', True), ('active', '=', False),
                        ]
                        candidate = request.env['res.partner']
                        if billing_phone:
                            candidate = request.env['res.partner'].sudo().search(
                                search_domain + [('phone', '=', billing_phone)],
                                limit=1,
                            )
                        if not candidate and billing_street:
                            candidate = request.env['res.partner'].sudo().search(
                                search_domain + [
                                    ('street', '=', billing_street),
                                    ('city', '=', billing_city or ''),
                                ],
                                limit=1,
                            )

                        if candidate:
                            candidate.sudo().write(billing_partner_vals)
                            candidate.invalidate_recordset(
                                ['name', 'display_name', 'active']
                            )
                            billing_partner = candidate
                        else:
                            billing_partner = request.env['res.partner'].sudo().create(
                                billing_partner_vals
                            )

                    order_sudo.sudo().write({
                        'partner_invoice_id': billing_partner.id
                    })

            self._force_order_draft(
                order_sudo, reason='After setting partner_invoice_id'
            )

            # ── 7. Validate Provider ──────────────────────────────────────
            if not provider_id:
                payment_values = self._get_shop_payment_values(order_sudo)
                self._force_order_draft(
                    order_sudo,
                    reason='After _get_shop_payment_values fallback',
                )
                providers_sudo = payment_values.get('providers_sudo')
                if providers_sudo:
                    provider_id = providers_sudo[0].id
                else:
                    _logger.error("No payment providers available.")
                    return request.redirect('/shop/checkout')

            try:
                provider_id_int = int(provider_id)
            except (ValueError, TypeError):
                _logger.error("Invalid provider_id: %s", provider_id)
                return request.redirect('/shop/checkout')

            payment_method_id_int = None
            if payment_method_id:
                try:
                    payment_method_id_int = int(payment_method_id)
                except (ValueError, TypeError):
                    pass

            provider = request.env['payment.provider'].sudo().browse(provider_id_int)
            if not provider.exists():
                _logger.error("Provider ID %s does not exist.", provider_id_int)
                return request.redirect('/shop/checkout')

            if not payment_method_id_int and provider:
                if hasattr(provider, 'payment_method_ids') and provider.payment_method_ids:
                    payment_method_id_int = provider.payment_method_ids[0].id
                else:
                    pm = request.env['payment.method'].sudo().search(
                        [('provider_ids', 'in', [provider.id])], limit=1
                    )
                    if pm:
                        payment_method_id_int = pm.id
                    else:
                        pm_any = request.env['payment.method'].sudo().search([], limit=1)
                        if pm_any:
                            payment_method_id_int = pm_any.id

            # Security validation
            options_data = self._get_checkout_options_data(order_sudo)
            self._force_order_draft(
                order_sudo, reason='After security validation'
            )

            allowed_provider_ids = {
                option.get('provider_id')
                for option in options_data.get('payment_options', [])
                if option.get('provider_id')
            }

            if provider_id_int not in allowed_provider_ids:
                _logger.warning(
                    "❌ BLOCKED provider '%s' (id=%s). Allowed=%s",
                    provider.name, provider_id_int, allowed_provider_ids,
                )
                return request.redirect('/shop/checkout')

            # ── 8. Create Transaction ─────────────────────────────────────
            try:
                tx_sudo = self._create_transaction(
                    provider_id=provider_id_int,
                    payment_method_id=payment_method_id_int,
                    token_id=None,
                    amount=order_sudo.amount_total,
                    currency_id=order_sudo.currency_id.id,
                    partner_id=order_sudo.partner_invoice_id.id,
                    flow='redirect',
                    tokenization_requested=False,
                    landing_route='/shop/single_checkout/confirmation',
                    is_validation=False,
                    custom_create_values={
                        'sale_order_ids': [Command.set([order_sudo.id])]
                    },
                )
            except Exception as e:
                _logger.error(
                    "Transaction creation failed: %s", e, exc_info=True
                )
                return request.redirect('/shop/checkout')

            self._force_order_draft(
                order_sudo, reason='Immediately after _create_transaction'
            )
            self._force_tx_pending(tx_sudo, reason='Manual order review flow')
            self._force_order_draft(
                order_sudo, reason='After forcing tx to pending'
            )

            # ── 9. Session — CRITICAL FIX ─────────────────────────────────
            # ✅ sale_last_order_id rakho — confirmation page ko chahiye
            request.session['sale_last_order_id'] = order_sudo.id

            # ✅ CRITICAL: Yeh 2 keys POST-PROCESSING trigger karti hain
            # Inhe explicitly REMOVE karo
            request.session.pop('__website_sale_last_tx_id', None)
            request.session.pop('__payment_monitored_tx_id__', None)

            _logger.info(
                "✅ Order %s stays DRAFT | TX %s → pending | Provider='%s'",
                order_sudo.name,
                tx_sudo.reference,
                provider.name,
            )

            return request.redirect('/shop/single_checkout/confirmation')

        except Exception as e:
            _logger.error(
                "single_checkout_process_payment error: %s", e, exc_info=True
            )
            try:
                if request.env.cr.in_failed_transaction():
                    request.env.cr.rollback()
            except Exception:
                pass
            return request.redirect('/shop/checkout')

    # ════════════════════════════════════════════════════════════════════════
    # 🔒 SAFE CONFIRMATION ROUTE
    # ════════════════════════════════════════════════════════════════════════

    @http.route(
        '/shop/single_checkout/confirmation',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def single_checkout_confirmation(self, **kwargs):
        """
        Safe intermediate route.
        Session keys hata do, phir default /shop/confirmation pe jao.
        """
        order_sudo = request.cart
        if not order_sudo:
            order_id = request.session.get('sale_last_order_id')
            if order_id:
                order_sudo = request.env['sale.order'].sudo().browse(
                    int(order_id)
                )

        if not order_sudo or not order_sudo.exists():
            return request.redirect('/shop')

        # 🔒 Force draft
        self._force_order_draft(
            order_sudo, reason='Confirmation intermediate route'
        )

        # ✅ CRITICAL: Yeh 2 keys hata do — POST PROCESSING TRIGGER HOTI HAIN
        request.session.pop('__website_sale_last_tx_id', None)
        request.session.pop('__payment_monitored_tx_id__', None)

        # ✅ Ab safe hai default page use karo
        return request.redirect('/shop/confirmation')

    # ════════════════════════════════════════════════════════════════════════
    # 🔒 /shop/confirmation OVERRIDE — Auto-confirm rok do
    # ════════════════════════════════════════════════════════════════════════

    @http.route(
        '/shop/confirmation',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def shop_payment_confirmation(self, **kwargs):
        """
        Odoo ke default /shop/confirmation ko override karo.
        Order confirm hone se rokta hai, phir default page dikhata hai.
        """
        order_id = request.session.get('sale_last_order_id')

        if order_id:
            try:
                order_sudo = request.env['sale.order'].sudo().browse(int(order_id))
                if order_sudo.exists():
                    # 🔒 Confirm hone se pehle force draft
                    self._force_order_draft(
                        order_sudo,
                        reason='/shop/confirmation intercepted — keeping as Quotation'
                    )
                    # ✅ Keys dobara hata do safety ke liye
                    request.session.pop('__website_sale_last_tx_id', None)
                    request.session.pop('__payment_monitored_tx_id__', None)
            except Exception as e:
                _logger.error(
                    "Error in shop_payment_confirmation override: %s", e
                )

        # ✅ Default confirmation page dikhao — order confirm nahi hoga
        return super().shop_payment_confirmation(**kwargs)

    # ════════════════════════════════════════════════════════════════════════
    # 🔒 Payment Status Poll — Post-processing kabhi nahi chalega
    # ════════════════════════════════════════════════════════════════════════

    @http.route('/payment/status/poll', type='jsonrpc', auth='public')
    def payment_status_poll_custom_override(self, **_kwargs):
        monitored_tx_id = request.session.get('__payment_monitored_tx_id__')
        monitored_tx = (
            request.env['payment.transaction'].sudo()
            .browse(monitored_tx_id).exists()
            if monitored_tx_id else False
        )

        if not monitored_tx:
            return {'state': 'error'}

        # 🔒 Poll ke dauran har linked order ko draft rakho
        for order in monitored_tx.sale_order_ids:
            self._force_order_draft(
                order,
                reason=f'Payment status poll — tx {monitored_tx.reference}',
            )

        # 🔒 TX bhi pending hi rahay
        self._force_tx_pending(
            monitored_tx,
            reason='Payment status poll — manual review required',
        )

        _logger.info(
            "⏸ Poll: Post-process SKIPPED for tx %s (state=%s).",
            monitored_tx.reference,
            monitored_tx.state,
        )

        return {
            'provider_code': monitored_tx.provider_code,
            'state': monitored_tx.state,
            'landing_route': False,
        }