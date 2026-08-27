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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WeatherVulnerableSite(Document):
    def validate(self):
        try:
            lat, lng = float(self.latitude), float(self.longitude)
        except (TypeError, ValueError):
            frappe.throw("latitude and longitude must be numbers")
            return
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            frappe.throw(f"coordinates out of range: {lat}, {lng}")

    def on_update(self):
        # Insert AND update: auto-register/refresh this site's grid cell as
        # a Weather Watch Location (the get_weather_warnings registration
        # pattern) and stamp the watch_location link. Guaranteed never to
        # raise - the hourly pass self-heals any missed coverage.
        from ...warnings_engine.sites import on_site_saved
        on_site_saved(self)
