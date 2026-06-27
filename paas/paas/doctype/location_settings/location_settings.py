# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class LocationSettings(Document):
    def before_save(self):
        if self.location:
            try:
                # GeoJSON format: {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [long, lat]}, ...}]}
                # OR simple geometry: {"type": "Point", "coordinates": [long, lat]}
                # Frappe Geolocation field typically saves as a JSON string of
                # a FeatureCollection or Geometry.

                geo_data = json.loads(self.location)

                # Handle FeatureCollection
                if geo_data.get("type") == "FeatureCollection" and geo_data.get(
                    "features"
                ):
                    geometry = geo_data["features"][0].get("geometry", {})
                else:
                    geometry = geo_data

                if geometry.get("type") == "Point" and geometry.get("coordinates"):
                    # coordinates are [longitude, latitude]
                    self.location_longitude = geometry["coordinates"][0]
                    self.location_latitude = geometry["coordinates"][1]
            except Exception:
                frappe.log_error("Error parsing location in Location Settings")
        elif self.location_latitude and self.location_longitude:
            # Construct GeoJSON if location is missing but lat/long exist
            self.location = json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    self.location_longitude,
                                    self.location_latitude,
                                ],
                            },
                        }
                    ],
                }
            )
