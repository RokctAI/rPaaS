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

"""Structured endpoint telemetry for the tender SDK (assessment plan #5).

One helper for all 22 whitelisted endpoints, replacing the bare
``print(..., file=sys.stderr)`` lines: each API call logs ONE structured
JSON event through ``frappe.logger("tender.api")``, so trace ids become
queryable in the site logs (fleet practice, cf. the mature SDKs' admin
telemetry) instead of vanishing into stderr.

Degradation contract: telemetry must NEVER break a request. On any logging
failure (no logger on a stubbed frappe, no site context) the helper falls
back to the exact legacy single-line stderr format
``[tender.api] {endpoint} k=v ... trace_id={trace_id}``. Endpoint shims
import this module with a guarded ``try/except`` that recreates the same
stderr fallback inline, so the standalone verify suites (which exec the
shims against an in-memory frappe stub with no composed package to import
from) keep working untouched.
"""

import json
import sys

import frappe

LOGGER_NAME = "tender.api"


def log_api_call(endpoint, trace_id=None, **fields):
	"""Logs one structured api_call event for an endpoint invocation.

	``endpoint`` is the endpoint function name; ``trace_id`` the request's
	X-Trace-Id (or None); ``fields`` any endpoint-specific context (bid,
	slug, mode, ...) - keep them aggregate/identifier-level, never payload
	bodies. Writes a JSON line via frappe.logger so the site's log
	machinery (rotation, levels, grepping by trace_id) applies; degrades to
	the legacy stderr line on any failure and never raises.
	"""
	try:
		payload = {"event": "api_call", "endpoint": endpoint, "trace_id": trace_id}
		payload.update(fields)
		frappe.logger(LOGGER_NAME, allow_site=True).info(
			json.dumps(payload, default=str, sort_keys=True)
		)
	except Exception:
		try:
			extras = "".join(f" {key}={value}" for key, value in fields.items())
			print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)
		except Exception:
			pass  # telemetry must never break the request
