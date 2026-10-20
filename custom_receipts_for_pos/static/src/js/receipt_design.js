/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { useState, Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";


patch(PosOrder.prototype, {
    export_for_printing() {
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
                ticket: pl.ticket || "",
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
    }
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

patch(OrderReceipt.prototype, {
    setup(){
        super.setup();
        this.state = useState({
            template: true,
        });
        this.pos = useState(useService("pos"));

        const self = this;
        let originalProps = this.props;
        let patchedProps = new Proxy(originalProps, {
            get(target, prop) {
                if (prop === 'data' || prop === 'receipt') {
                    return target.order ? target.order.export_for_printing() : {};
                }
                if (prop === 'paymentlines') {
                    return target.order ? target.order.export_for_printing().paymentlines : [];
                }
                if (prop === 'formatCurrency') {
                    return self.formatCurrency ? self.formatCurrency.bind(self) : (val) => val;
                }
                return target[prop];
            }
        });
        Object.defineProperty(this, 'props', {
            get() {
                return patchedProps;
            },
            set(val) {
                originalProps = val;
                patchedProps = new Proxy(val, {
                    get(target, prop) {
                        if (prop === 'data' || prop === 'receipt') {
                            return target.order ? target.order.export_for_printing() : {};
                        }
                        if (prop === 'paymentlines') {
                            return target.order ? target.order.export_for_printing().paymentlines : [];
                        }
                        if (prop === 'formatCurrency') {
                            return self.formatCurrency ? self.formatCurrency.bind(self) : (val) => val;
                        }
                        return target[prop];
                    }
                });
            },
            configurable: true
        });
    },
    get templateProps() {
        const order = this.props.order || this.pos.get_order();
        const data = order ? order.export_for_printing() : {};
        return {
            data: data,
            order: order,
            receipt: data,
            orderlines: order ? order.lines : [],
            paymentlines: data.paymentlines || []
        };
    },
    get templateComponent() {
        var mainRef = this;
        return class extends Component {
            setup() {}
            static template = xml`${mainRef.pos.config.design_receipt}`
        };
    },
    get isTrue() {
        return this.env.services.pos.config.is_custom_receipt;
    },
    get showTaxGroupLabels() {
        return this.doesAnyOrderlineHaveTaxLabel ? this.doesAnyOrderlineHaveTaxLabel() : false;
    },
    get order_change() {
        return this.props.order ? this.props.order.change : 0;
    }
});

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        return false;
    }
});
