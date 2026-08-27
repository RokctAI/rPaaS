# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Phase-2 control->SDK extraction (2026-08-24): moved here verbatim from
# control/control/seeds/scripts/seed_paas_juvo_settings.py (RokctAI/control).
# The Laravel-era juvo seed DUMPS (control/control/seeds/*.json, ~380k lines)
# deliberately REMAIN in the control repo, pending Ray's archive/delete
# decision. This script does not read those dumps - it seeds tenant settings
# doctypes from site config (frappe.conf) and inline data only, so no dump
# path is needed here. The dumps are consumed separately by rcore's seeding
# machinery from apps/control/control/seeds/.

import frappe
import json


def get_conf_credential(key):
    """Read a credential from site config, failing loudly if it is missing."""
    value = frappe.conf.get(key)
    if not value:
        frappe.throw(
            f"Missing required site config key '{key}'. "
            f"Add it to site_config.json (or common_site_config.json) before running this seed."
        )
    return value


def execute():
    if frappe.local.site == "juvo.tenant.rokct.ai":
        google_api_key = get_conf_credential("google_api_key")

        # Seed Settings (General)
        settings = frappe.get_doc("Settings")
        settings.project_title = "Juvo"
        settings.deliveryman_order_acceptance_time = 5
        settings.service_fee = 0
        settings.recommended_count = 1
        settings.tip_type = "all"
        settings.favicon = "https://s3.juvo.app/public/images/languages/101-1713223589.webp"
        settings.logo = "https://s3.juvo.app/public/images/languages/101-1713223586.webp"
        settings.save(ignore_permissions=True)

        # Seed Location Settings
        loc = frappe.get_doc("Location Settings")
        loc.google_map_key = google_api_key
        loc.location_latitude = -22.342385264868007
        loc.location_longitude = 30.016277228408626
        loc.save(ignore_permissions=True)

        # Seed Delivery Settings
        delivery = frappe.get_doc("Delivery Settings")

        coords = [
            [30.054817466453056,-22.356647441808036],
            [30.04656028600071,-22.330132284329398],
            [30.032655714467506,-22.315840587785814],
            [30.012742994740943,-22.321716240213075],
            [30.00158500523899,-22.332037733263448],
            [29.989397047475318,-22.342676011365945],
            [29.993688581899146,-22.353631001533845],
            [30.001241682485084,-22.366807602160147],
            [30.016519545033912,-22.37791942870363],
            [30.02905082555149,-22.375697134358756],
            [30.044672010854224,-22.366331361201937],
            [30.054817466453056,-22.356647441808036]
        ]

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
                }
            ]
        }

        delivery.default_delivery_zone = json.dumps(geojson)
        delivery.save(ignore_permissions=True)

        # Seed Auth Settings
        auth = frappe.get_doc("Auth Settings")
        auth.otp_expire_time = 5
        auth.save(ignore_permissions=True)

        # Seed Reservation Settings
        res = frappe.get_doc("Reservation Settings")
        res.reservation_time_durations = "30"
        res.reservation_before_time = 1
        res.notification_time_before = 30
        res.min_reservation_time = 1
        res.save(ignore_permissions=True)

        # Seed QR Code Settings
        qr = frappe.get_doc("QR Code Settings")
        qr.qrcode_base_url = "https://qr.juvo.app/"
        qr.qrcode_type = "w2"
        qr.split_min = 100
        qr.split_max = 500
        qr.save(ignore_permissions=True)

        # Seed Design Settings
        design = frappe.get_doc("Design Settings")
        design.ui_type = "5"
        design.save(ignore_permissions=True)

        # Seed Footer Settings
        footer = frappe.get_doc("Footer Settings")
        footer.phone = "+27790345401"
        footer.address = "Musina, South Africa"
        footer.footer_text = "Juvo Platforms"
        footer.save(ignore_permissions=True)

        # Seed Social Settings
        social = frappe.get_doc("Social Settings")
        social.facebook = "https://fb.com/SouthRiverSA"
        social.instagram = "https://Instagram.com/GOsouthZA"
        social.twitter = "https://twitter.com/GOsouthZA"
        social.save(ignore_permissions=True)

        # Seed App Settings
        app = frappe.get_doc("App Settings")
        app.vendor_app_ios = "#"
        app.vendor_app_android = "https://play.google.com/store/apps/details?id=app.juvo.vendor"
        app.delivery_app_ios = "#"
        app.delivery_app_android = "https://play.google.com/store/apps/details?id=app.juvo.driver"
        app.customer_app_ios = "https://web.juvo.app/"
        app.customer_app_android = "https://play.google.com/store/apps/details?id=app.juvo.food"
        app.save(ignore_permissions=True)

        # Seed Permission Settings
        perms = frappe.get_doc("Permission Settings")
        perms.auto_approve_orders = 1
        perms.enable_refund_system = 1
        perms.auto_approve_parcel_orders = 1
        perms.enable_refund_deletion = 1
        perms.enable_auto_assign_deliveryman = 1
        perms.enable_auto_print_order = 1
        perms.enable_driver_to_edit_credentials = 1
        perms.require_phone_for_order = 1
        perms.auto_approve_categories = 1
        perms.auto_approve_products = 1
        perms.enable_parcel_system = 1
        perms.enable_referral_earnings = 1
        perms.enable_reservations = 1
        perms.enable_vendor_subscriptions = 0
        perms.enable_commission_model = 0
        perms.enable_group_orders = 1
        perms.enable_paas_lending = 0

        perms.blog_active = 1
        perms.prompt_email_modal = 0
        perms.aws_active = 0
        perms.is_demo = 0

        perms.save(ignore_permissions=True)

        # Seed Remote Config (Common)
        if not frappe.db.exists("Remote Config", {"app_type": "Common"}):
            frappe.get_doc({
                "doctype": "Remote Config",
                "site_name": "juvo.tenant.rokct.ai",
                "app_type": "Common",
                "google_api_key": google_api_key,
                "country_code_iso": "ZA",
                "locale_code_en": "en",
                "is_specific_number_enabled": 0,
                "is_number_length_always_same": 0,
                "show_flag": 1,
                "show_arrow_icon": 1
            }).insert(ignore_permissions=True)

        # Seed Remote Config (Customer)
        if not frappe.db.exists("Remote Config", {"app_type": "Customer"}):
            frappe.get_doc({
                "doctype": "Remote Config",
                "site_name": "juvo.tenant.rokct.ai",
                "app_type": "Customer",
                "base_url": "https://juvo.tenant.rokct.ai",
                "admin_page_url": "https://admin.juvo.app",
                "drawing_base_url": "https://s3.juvo.app/drawing/",
                "web_url": "https://web.juvo.app/",
                "uri_prefix": "juvo_customer",
                "show_google_poi_layer": 0,
                "demo_latitude": "-22.342385",
                "demo_longitude": "30.016277",
                "new_shop_days": 14
            }).insert(ignore_permissions=True)
