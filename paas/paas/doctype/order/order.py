# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class Order(Document):
    def before_save(self):
        self.calculate_totals()

    def calculate_totals(self):
        # Calculate total price from order items
        total_price = sum(item.price * item.quantity for item in self.order_items)
        total_discount = sum(item.discount or 0 for item in self.order_items)

        # Calculate shop tax
        # Calculate shop tax
        shop_tax = 0
        if self.shop:
            shop = frappe.get_doc("Shop", self.shop)
            if shop.tax:
                shop_tax = total_price * (shop.tax / 100)

        total_price += shop_tax

        # Apply coupon
        if self.coupon_code:
            coupon = frappe.db.get_value(
                "Coupon",
                {"code": self.coupon_code},
                ["discount_type", "discount_amount"],
                as_dict=True,
            )
            if coupon:
                if coupon.discount_type == "Percentage":
                    coupon_discount = total_price * (coupon.discount_amount / 100)
                else:
                    coupon_discount = coupon.discount_amount
                total_discount += coupon_discount

        total_price -= total_discount

        # Add service fee
        service_fee = 0
        if frappe.db.exists("DocType", "Permission Settings"):
            service_fee = (
                frappe.db.get_single_value("Permission Settings", "service_fee") or 0
            )

        total_price += service_fee
        total_price += self.delivery_fee or 0

        # Commission fee
        commission_fee = 0
        if self.shop:
            # Assuming commission percentage is stored on the Shop doctype
            if shop.percentage:
                commission_fee = total_price * (shop.percentage / 100)

        self.total_price = total_price
        self.tax = shop_tax
        self.total_discount = total_discount
        self.service_fee = service_fee
        self.commission_fee = commission_fee
