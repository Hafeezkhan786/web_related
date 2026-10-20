/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";

patch(PosStore.prototype, {
    async pay() {
        const currentOrder = this.getOrder();

        if (currentOrder && currentOrder.lines.length > 0) {
            // Check if FBR POS Charges product already exists
            const hasFBRCharges = currentOrder.lines.some(line => {
                const productName = line.product_id?.display_name || line.product_id?.name || "";
                return productName.includes("FBR POS Charges");
            });
            
            if (!hasFBRCharges) {
                const fbrProduct = this.models["product.product"].find((p) => {
                    const name = p.display_name || p.name || "";
                    return name.includes("FBR POS Charges");
                });
                
                if (fbrProduct) {
                    await this.addLineToOrder({
                        product_id: fbrProduct,
                        product_tmpl_id: fbrProduct.product_tmpl_id,
                        qty: 1,
                        price_unit: fbrProduct.lst_price,
                    }, currentOrder, { force: true }, false);
                } else {
                    console.warn("FBR POS Charges product not found in POS.");
                }
            }
        }

        return super.pay(...arguments);
    }
});

patch(PosOrder.prototype, {
    setup(defaultObj, options) {
        super.setup(...arguments);
        // Safely set data
        this.fbr_invoice_number = this.fbr_invoice_number || "";
        this.fbr_status = this.fbr_status || "draft";
        this.fbr_error_message = this.fbr_error_message || "";

        // Start monitoring for FBR data updates
        this._start_fbr_monitoring();
    },

    _start_fbr_monitoring() {
        // Wait a moment for backendId to be set, then start monitoring
        setTimeout(() => {
            if (this.backendId) {
                console.log('FBR: Starting monitoring for backendId:', this.backendId);
                // Check for FBR data every 2 seconds after order validation
                this.fbr_monitor_interval = setInterval(() => {
                    this._check_fbr_update();
                }, 2000);
            } else if (this.fbr_status === 'posted') {
                console.log('FBR: Already has invoice number:', this.fbr_invoice_number);
            } else {
                console.log('FBR: No backendId available yet, will retry...');
                // Retry after 2 seconds if no backendId
                setTimeout(() => this._start_fbr_monitoring(), 2000);
            }
        }, 1000);
    },

    async _check_fbr_update() {
        try {
            console.log('FBR: Checking update for backendId:', this.backendId);
            // Fetch updated order data from backend
            const result = await this.env.services.orm.searchRead('pos.order', [['id', '=', this.backendId]], ['fbr_invoice_number', 'fbr_status', 'fbr_error_message']);

            if (result && result.length > 0) {
                const backendOrder = result[0];
                if (backendOrder.fbr_invoice_number && backendOrder.fbr_status === 'posted') {
                    // Update local order with FBR data
                    this.fbr_invoice_number = backendOrder.fbr_invoice_number;
                    this.fbr_status = backendOrder.fbr_status;
                    this.fbr_error_message = backendOrder.fbr_error_message || "";

                    console.log('FBR: Real-time update received:', {
                        fbr_invoice_number: this.fbr_invoice_number,
                        fbr_status: this.fbr_status
                    });

                    // Show notification
                    if (this.env && this.env.services && this.env.services.notification) {
                        this.env.services.notification.add(
                            _t("FBR Invoice Generated: %s", this.fbr_invoice_number),
                            { type: "success", sticky: false }
                        );
                    }

                    // Stop monitoring once we have the invoice number
                    clearInterval(this.fbr_monitor_interval);
                } else {
                    console.log('FBR: Order found but no FBR invoice yet');
                }
            } else {
                console.log('FBR: No order found with backendId:', this.backendId);
            }
        } catch (error) {
            console.error('FBR: Failed to check update:', error);
        }
    },

    // ZAROORI: Local storage se load karne ke liye
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.fbr_invoice_number = json.fbr_invoice_number || "";
        this.fbr_status = json.fbr_status || "draft";
        this.fbr_error_message = json.fbr_error_message || "";
    },

    // ZAROORI: Local storage/Backend mein save karne ke liye
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.fbr_invoice_number = this.fbr_invoice_number || "";
        json.fbr_status = this.fbr_status || "draft";
        json.fbr_error_message = this.fbr_error_message || "";
        return json;
    },

    export_for_printing_base() {
        const order = this;
        const pos = this.env?.services?.pos || {};
        const cashierName = order.getCashierName ? order.getCashierName() : (pos.cashier?.name || "");

        const orderlines = order.lines.map(line => {
            const discount = line.getDiscount ? line.getDiscount() : (line.discount || 0);
            const unitPrice = typeof line.displayPriceUnit === 'number' ? Math.round(line.displayPriceUnit * 100) / 100 : line.displayPriceUnit;
            const price = typeof line.displayPrice === 'number' ? Math.round(line.displayPrice * 100) / 100 : line.displayPrice;
            const price_without_discount = line.displayPriceUnitNoDiscount * line.qty;

            return {
                id: line.id,
                uuid: line.uuid,
                productName: line.product_id?.display_name || line.full_product_name || "",
                qty: line.qty,
                unit: line.product_id?.uom_id?.name || "",
                unitPrice: unitPrice,
                price: price,
                discount: discount,
                price_without_discount: price_without_discount,
                oldUnitPrice: line.displayPriceUnitNoDiscount,
                originalUnitPrice: typeof line.originalUnitPrice === 'number' ? Math.round(line.originalUnitPrice * 100) / 100 : line.originalUnitPrice,
                discountPercentage: line.discountPercentage,
                packaging: line.packaging_id?.name || "",
                customerNote: line.customerNote || line.customer_note || "",
            };
        });

        const paymentlines = order.payment_ids.map(pl => {
            return {
                id: pl.id,
                uuid: pl.uuid,
                name: pl.payment_method_id?.name || "",
                amount: pl.getAmount(),
            };
        });

        const taxTotals = {
            has_tax_groups: order.prices?.taxDetails?.has_tax_groups || false,
            subtotals: order.prices?.taxDetails?.subtotals || [],
            order_total: order.priceIncl,
            order_rounding: order.appliedRounding,
            total_amount_currency: order.totalDue,
            order_change: order.change,
            same_tax_base: order.prices?.taxDetails?.same_tax_base
        };

        const tax_details = [];
        if (order.prices?.taxDetails?.subtotals) {
            for (const subtotal of order.prices.taxDetails.subtotals) {
                if (subtotal.tax_groups) {
                    for (const tg of subtotal.tax_groups) {
                        tax_details.push({
                            tax: { name: tg.group_name },
                            amount: tg.tax_amount_currency
                        });
                    }
                }
            }
        }

        const dateStr = order.date_order ? (order.date_order.toFormat ? order.date_order.toFormat("yyyy-MM-dd HH:mm:ss") : order.date_order) : "";

        return {
            headerData: {
                company: order.company || pos.company || {},
                cashier: cashierName ? _t("Served by %s", cashierName) : "",
                header: order.config?.receipt_header || "",
                fbr_invoice_number: order.fbr_invoice_number || "",
                fbr_status: order.fbr_status || "draft",
                fbr_error_message: order.fbr_error_message || "",
            },
            orderlines: orderlines,
            paymentlines: paymentlines,
            taxTotals: taxTotals,
            tax_details: tax_details,
            total_discount: order.currency ? order.currency.round(order.lines.reduce((sum, line) => {
                const original = line.originalUnitPrice || 0;
                const current = line.displayPriceUnit || 0;
                if (original > current) {
                    return sum + (original - current) * line.qty;
                }
                return sum;
            }, 0)) : 0,
            pos_qr_code: order.access_token ? generateQRCodeDataUrl(`${order.config?._base_url}/pos/ticket/validate?access_token=${order.access_token}`) : "",
            ticket_code: order.ticket_code || "",
            base_url: order.config?._base_url || "",
            header_note: order.header_note || "",
            footer: order.config?.receipt_footer || "",
            footer_html: "",
            shippingDate: order.shipping_date ? (order.formatDateOrTime ? order.formatDateOrTime('shipping_date', 'date') : order.shipping_date) : "",
            shipping_date: order.shipping_date || "",
            name: order.name || "",
            date: dateStr,
            amount_total: order.priceIncl,
            total_without_tax: order.priceExcl,
            total_tax: order.priceIncl - order.priceExcl,
            change: order.change || 0,

            fbr_invoice_number: order.fbr_invoice_number || "",
            fbr_status: order.fbr_status || "draft",
            fbr_error_message: order.fbr_error_message || "",
            has_fbr_logo: pos.config?.logo ? true : false,
            fbr_company_id: order.company?.id || pos.company?.id || 1,
        };
    },

    export_for_printing() {
        const result = typeof super.export_for_printing === 'function'
            ? super.export_for_printing(...arguments)
            : this.export_for_printing_base();

        console.log('FBR: export_for_printing called, checking FBR data...');
        console.log('FBR: Current fbr_invoice_number:', this.fbr_invoice_number);
        console.log('FBR: Backend ID:', this.backendId);
        console.log('FBR: Order name:', this.name);

        // If no FBR invoice number, start async fetch in background
        if (!this.fbr_invoice_number && this.name) {
            console.log('FBR: No local invoice number, starting background fetch...');
            // Start fetch in background without blocking
            this._fetch_fbr_background(this.name);
        }

        result.fbr_invoice_number = this.fbr_invoice_number;
        result.fbr_status = this.fbr_status;
        result.fbr_error_message = this.fbr_error_message;

        // Add FBR data to headerData for receipt template (like SRB)
        if (result.headerData) {
            result.headerData.fbr_invoice_number = this.fbr_invoice_number;
            result.headerData.fbr_status = this.fbr_status;
            result.headerData.fbr_error_message = this.fbr_error_message;
        }

        console.log('FBR: Final export data:', {
            fbr_invoice_number: result.fbr_invoice_number,
            fbr_status: result.fbr_status,
            headerData_fbr: result.headerData?.fbr_invoice_number
        });

        return result;
    },

    async _fetch_fbr_background(orderName) {
        // Wait 3 seconds for order to be processed
        await new Promise(resolve => setTimeout(resolve, 3000));
        await this._fetch_fbr_by_order_name(orderName);

        // Trigger receipt update if we found FBR data
        if (this.fbr_invoice_number) {
            console.log('FBR: Background fetch successful, FBR invoice number is now available');
            // The receipt will automatically update on next render since we updated the order data
        }
    },

    _retry_fbr_fetch(orderName, attempt) {
        const delays = [2000, 4000, 6000, 8000]; // Increasing delays: 2s, 4s, 6s, 8s

        if (attempt >= delays.length) {
            console.log('FBR: Max retries reached, giving up');
            return;
        }

        setTimeout(async () => {
            console.log(`FBR: Retry attempt ${attempt + 1}/${delays.length} for order: ${orderName}`);
            await this._fetch_fbr_by_order_name(orderName, attempt + 1);
        }, delays[attempt]);
    },

    async _fetch_fbr_by_order_name(orderName) {
        try {
            console.log('FBR: Searching for order by name:', orderName);

            // Try searching by name first
            let result = await this.env.services.orm.searchRead('pos.order', [['name', '=', orderName]], ['fbr_invoice_number', 'fbr_status', 'fbr_error_message', 'id']);

            // If not found, try searching by pos_reference (this is usually the correct field)
            if (!result || result.length === 0) {
                console.log('FBR: Not found by name, trying pos_reference...');
                result = await this.env.services.orm.searchRead('pos.order', [['pos_reference', '=', orderName]], ['fbr_invoice_number', 'fbr_status', 'fbr_error_message', 'id']);
            }

            // If still not found, try a broader search to see what orders exist
            if (!result || result.length === 0) {
                console.log('FBR: Still not found, searching recent orders...');
                const recentOrders = await this.env.services.orm.searchRead('pos.order', [], ['name', 'pos_reference', 'fbr_invoice_number', 'fbr_status', 'id'], { limit: 5, order: 'id desc' });
                console.log('FBR: Recent orders:', recentOrders);
            }

            if (result && result.length > 0) {
                const backendOrder = result[0];
                if (backendOrder.fbr_invoice_number && backendOrder.fbr_status === 'posted') {
                    this.fbr_invoice_number = backendOrder.fbr_invoice_number;
                    this.fbr_status = backendOrder.fbr_status;
                    this.fbr_error_message = backendOrder.fbr_error_message || "";

                    console.log('FBR: Found by order! Invoice:', {
                        fbr_invoice_number: this.fbr_invoice_number,
                        fbr_status: this.fbr_status,
                        search_field: result.length > 0 ? 'found' : 'not found'
                    });

                    // Show notification
                    if (this.env && this.env.services && this.env.services.notification) {
                        this.env.services.notification.add(
                            _t("FBR Invoice Found: %s", this.fbr_invoice_number),
                            { type: "success", sticky: false }
                        );
                    }
                } else {
                    console.log('FBR: Order found but no FBR invoice yet');
                }
            } else {
                console.log('FBR: No order found with name or pos_reference:', orderName);
            }
        } catch (error) {
            console.error('FBR: Failed to search by order name:', error);
        }
    },

    _fetch_fbr_from_backend_sync() {
        console.log('FBR: _fetch_fbr_from_backend_sync called');
        try {
            // Try to get FBR data from the order if it was updated after payment
            if (this.pos && this.pos.get_order) {
                const orders = this.pos.get_order_list();
                console.log('FBR: Found orders:', orders.length, 'Looking for backendId:', this.backendId);
                const currentOrder = orders.find(order => order.backendId === this.backendId);
                if (currentOrder && currentOrder.fbr_invoice_number) {
                    this.fbr_invoice_number = currentOrder.fbr_invoice_number;
                    this.fbr_status = currentOrder.fbr_status || "posted";
                    this.fbr_error_message = currentOrder.fbr_error_message || "";

                    console.log('FBR: Found updated data in local orders:', {
                        fbr_invoice_number: this.fbr_invoice_number,
                        fbr_status: this.fbr_status
                    });
                } else {
                    console.log('FBR: No updated data found in local orders');
                }
            }
        } catch (error) {
            console.error('FBR: Failed to get local data:', error);
        }
    },

    async _fetch_fbr_from_backend() {
        try {
            // Fetch updated order data from backend
            const result = await this.pos.data.call('pos.order', 'read', [this.backendId], {
                fields: ['fbr_invoice_number', 'fbr_status', 'fbr_error_message']
            });

            if (result && result.length > 0) {
                const backendOrder = result[0];
                this.fbr_invoice_number = backendOrder.fbr_invoice_number || "";
                this.fbr_status = backendOrder.fbr_status || "draft";
                this.fbr_error_message = backendOrder.fbr_error_message || "";

                console.log('FBR: Fetched fresh data:', {
                    fbr_invoice_number: this.fbr_invoice_number,
                    fbr_status: this.fbr_status
                });
            }
        } catch (error) {
            console.error('FBR: Failed to fetch from backend:', error);
        }
    },


    get_fbr_status_display() {
        switch (this.fbr_status) {
            case 'draft': return _t("Not sent to FBR");
            case 'posted': return _t("Posted to FBR");
            case 'failed': return _t("Failed - %s", this.fbr_error_message || "Unknown error");
            case 'pending': return _t("Pending FBR response");
            default: return _t("Unknown status");
        }
    },
});

patch(PosOrderline.prototype, {
    get productName() {
        return this.product_id?.display_name || this.full_product_name || "";
    },
    get unit() {
        return this.product_id?.uom_id?.name || "";
    },
    get unitPrice() {
        return typeof this.displayPriceUnit === 'number' ? Math.round(this.displayPriceUnit * 100) / 100 : this.displayPriceUnit;
    },
    get price() {
        return typeof this.displayPrice === 'number' ? Math.round(this.displayPrice * 100) / 100 : this.displayPrice;
    },
    get price_without_discount() {
        return this.displayPriceUnitNoDiscount * this.qty;
    },
    get oldUnitPrice() {
        return this.displayPriceUnitNoDiscount;
    },
    get customerNote() {
        return this.customer_note || "";
    },
    get packaging() {
        return this.packaging_id?.name || "";
    },
    get originalUnitPrice() {
        const config = this.config;
        if (!config || !this.product_id) {
            return typeof this.displayPriceUnit === 'number' ? Math.round(this.displayPriceUnit * 100) / 100 : this.displayPriceUnit;
        }
        try {
            const taxDetails = this.product_id.getTaxDetails({
                overridedValues: {
                    pricelist: false,
                    fiscalPosition: this.order_id?.fiscal_position_id || false,
                    priceExtra: this.getPriceExtra ? this.getPriceExtra() : (this.price_extra || 0)
                }
            });
            const basePriceWithTax = config.iface_tax_included === "total"
                ? taxDetails.total_included
                : taxDetails.total_excluded;
            const val = Math.max(basePriceWithTax, this.displayPriceUnitNoDiscount || 0);
            return typeof val === 'number' ? Math.round(val * 100) / 100 : val;
        } catch (e) {
            const val = Math.max(this.product_id.lst_price || 0, this.displayPriceUnitNoDiscount || 0);
            return typeof val === 'number' ? Math.round(val * 100) / 100 : val;
        }
    },
    get discountPercentage() {
        const original = this.originalUnitPrice;
        const current = this.displayPriceUnit;
        if (original && original > current) {
            return Math.round(((original - current) / original) * 100);
        }
        return 0;
    },
    get_discount() {
        return this.getDiscount ? this.getDiscount() : (this.discount || 0);
    },
    get_display_price() {
        return typeof this.displayPrice === 'number' ? Math.round(this.displayPrice * 100) / 100 : this.displayPrice;
    },
    get_quantity_str_with_unit() {
        const qtyStr = this.quantityStr?.qtyStr || String(this.qty);
        const unit = this.product_id?.uom_id?.name || "";
        return unit ? `${qtyStr} ${unit}` : qtyStr;
    }
});
