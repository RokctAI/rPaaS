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

"""Unit tests for the pure routing helpers (route_utils.py).

The module is deliberately frappe-free, so these tests run bench-
independently with plain `python3 -m unittest` (the
test_intercity_providers.py precedent).
"""

import importlib.util
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTE_UTILS_PATH = os.path.abspath(
    os.path.join(TESTS_DIR, "..", "src", "tenant", "api", "route", "route_utils.py")
)


def _load_route_utils():
    if "route_test_route_utils" in sys.modules:
        return sys.modules["route_test_route_utils"]
    spec = importlib.util.spec_from_file_location(
        "route_test_route_utils", ROUTE_UTILS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["route_test_route_utils"] = module
    spec.loader.exec_module(module)
    return module


route_utils = _load_route_utils()

# Sandton -> Rosebank -> Johannesburg CBD, roughly on a north-south line.
SANDTON = (-26.1076, 28.0567)
ROSEBANK = (-26.1438, 28.0436)
CBD = (-26.2041, 28.0473)
SOWETO = (-26.2678, 27.8585)


class TestHaversine(unittest.TestCase):
    def test_zero_distance(self):
        self.assertEqual(
            route_utils.haversine(SANDTON[0], SANDTON[1], *SANDTON), 0.0
        )

    def test_known_distance_sandton_to_cbd(self):
        distance = route_utils.haversine(*SANDTON, *CBD)
        # ~10.8km as the crow flies.
        self.assertGreater(distance, 9)
        self.assertLess(distance, 13)


class TestParseLocation(unittest.TestCase):
    def test_parses_json_string_with_latitude_longitude(self):
        self.assertEqual(
            route_utils.parse_location(
                '{"latitude": "-26.1", "longitude": 28.05}'
            ),
            (-26.1, 28.05),
        )

    def test_parses_lat_long_spellings(self):
        self.assertEqual(
            route_utils.parse_location({"lat": -26.1, "long": 28.05}),
            (-26.1, 28.05),
        )
        self.assertEqual(
            route_utils.parse_location({"lat": -26.1, "lng": 28.05}),
            (-26.1, 28.05),
        )

    def test_plain_text_and_malformed_values_return_none(self):
        self.assertIsNone(route_utils.parse_location("Customer: Jane"))
        self.assertIsNone(route_utils.parse_location(""))
        self.assertIsNone(route_utils.parse_location(None))
        self.assertIsNone(route_utils.parse_location("[1, 2]"))
        self.assertIsNone(
            route_utils.parse_location('{"latitude": "abc"}')
        )
        self.assertIsNone(route_utils.parse_location('{"latitude": 1}'))

    def test_nan_and_infinity_literals_return_none(self):
        # json.loads accepts NaN/Infinity literals; Infinity would blow
        # up haversine (math domain error), so both must be rejected.
        self.assertIsNone(
            route_utils.parse_location(
                '{"latitude": Infinity, "longitude": 20}'
            )
        )
        self.assertIsNone(
            route_utils.parse_location(
                '{"latitude": NaN, "longitude": 20}'
            )
        )
        self.assertFalse(
            route_utils.stop_has_coordinates(
                {"latitude": float("inf"), "longitude": 20}
            )
        )
        # An Infinity stop rides the flagged tail instead of crashing
        # the optimizer.
        ordered = route_utils.order_stops(
            (0.0, 0.0),
            [{"latitude": float("inf"), "longitude": 20.0}],
        )
        self.assertTrue(ordered[0].get("missing_coordinates"))

    def test_stop_has_coordinates_treats_zero_zero_as_unset(self):
        self.assertFalse(
            route_utils.stop_has_coordinates(
                {"latitude": 0, "longitude": 0}
            )
        )
        self.assertTrue(
            route_utils.stop_has_coordinates(
                {"latitude": -26.1, "longitude": 28.05}
            )
        )
        self.assertFalse(
            route_utils.stop_has_coordinates(
                {"latitude": None, "longitude": 28.05}
            )
        )


def _stop(name, coords=None, stop_type=None, pair_key=None):
    stop = {"ref_name": name}
    if coords:
        stop["latitude"], stop["longitude"] = coords
    else:
        stop["latitude"] = None
        stop["longitude"] = None
    if stop_type:
        stop["stop_type"] = stop_type
    if pair_key:
        stop["pair_key"] = pair_key
    return stop


class TestOrderStops(unittest.TestCase):
    def test_orders_nearest_first_from_start(self):
        # Start in Sandton: Rosebank is nearer than the CBD.
        ordered = route_utils.order_stops(
            SANDTON,
            [_stop("cbd", CBD), _stop("rosebank", ROSEBANK)],
        )
        self.assertEqual(
            [s["ref_name"] for s in ordered], ["rosebank", "cbd"]
        )
        self.assertEqual([s["sequence"] for s in ordered], [1, 2])
        self.assertIsNotNone(ordered[0]["distance_from_previous_km"])
        self.assertLess(
            ordered[0]["distance_from_previous_km"],
            ordered[1]["distance_from_previous_km"] + 20,
        )

    def test_no_start_keeps_first_stop_as_is(self):
        ordered = route_utils.order_stops(
            None,
            [_stop("cbd", CBD), _stop("rosebank", ROSEBANK),
             _stop("soweto", SOWETO)],
        )
        self.assertEqual(ordered[0]["ref_name"], "cbd")
        self.assertIsNone(ordered[0]["distance_from_previous_km"])
        # From the CBD, Rosebank is nearer than Soweto.
        self.assertEqual(
            [s["ref_name"] for s in ordered[1:]], ["rosebank", "soweto"]
        )

    def test_pickup_precedes_its_dropoff_even_when_dropoff_is_nearer(self):
        # Start right next to the drop-off: greedy alone would visit the
        # drop-off first; the pair constraint must hold it back.
        near_drop = (CBD[0] + 0.001, CBD[1] + 0.001)
        ordered = route_utils.order_stops(
            near_drop,
            [
                _stop("drop", CBD, stop_type="dropoff", pair_key="o1"),
                _stop("pick", SANDTON, stop_type="pickup", pair_key="o1"),
            ],
        )
        self.assertEqual(
            [s["ref_name"] for s in ordered], ["pick", "drop"]
        )

    def test_unpaired_stops_are_not_held_back(self):
        ordered = route_utils.order_stops(
            CBD,
            [
                _stop("pick", SOWETO, stop_type="pickup", pair_key="o1"),
                _stop("drop", SANDTON, stop_type="dropoff",
                      pair_key="o1"),
                _stop("plain", ROSEBANK),
            ],
        )
        # Rosebank (unpaired) is nearest and free to go first.
        self.assertEqual(ordered[0]["ref_name"], "plain")
        self.assertEqual(
            [s["ref_name"] for s in ordered[1:]], ["pick", "drop"]
        )

    def test_missing_coordinates_go_last_with_flag(self):
        ordered = route_utils.order_stops(
            SANDTON,
            [
                _stop("nowhere"),
                _stop("rosebank", ROSEBANK),
            ],
        )
        self.assertEqual(
            [s["ref_name"] for s in ordered], ["rosebank", "nowhere"]
        )
        self.assertTrue(ordered[1]["missing_coordinates"])
        self.assertNotIn("missing_coordinates", ordered[0])
        self.assertEqual([s["sequence"] for s in ordered], [1, 2])

    def test_dropoff_of_coordinate_less_pickup_rides_the_tail(self):
        ordered = route_utils.order_stops(
            SANDTON,
            [
                _stop("drop", CBD, stop_type="dropoff", pair_key="p1"),
                _stop("pick", None, stop_type="pickup", pair_key="p1"),
                _stop("rosebank", ROSEBANK),
            ],
        )
        self.assertEqual(ordered[0]["ref_name"], "rosebank")
        # Pickup (no coords) then its drop-off, both at the tail.
        self.assertEqual(
            [s["ref_name"] for s in ordered[1:]], ["pick", "drop"]
        )
        self.assertTrue(ordered[1]["missing_coordinates"])
        self.assertNotIn("missing_coordinates", ordered[2])

    def test_empty_and_none_inputs(self):
        self.assertEqual(route_utils.order_stops(SANDTON, []), [])
        self.assertEqual(route_utils.order_stops(None, None), [])

    def test_input_list_is_not_mutated(self):
        stops = [_stop("cbd", CBD), _stop("rosebank", ROSEBANK)]
        before = [dict(s) for s in stops]
        route_utils.order_stops(SANDTON, stops)
        self.assertEqual(stops, before)


if __name__ == "__main__":
    unittest.main()
