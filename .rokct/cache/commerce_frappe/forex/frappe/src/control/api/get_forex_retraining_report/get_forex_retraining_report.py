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

"""CONTROL-side ADMIN endpoint: the forex outcome ledger read back as a
retraining report — the same arrangement as zones' get_retraining_report.

ADMIN TELEMETRY ONLY. Requires the System Manager role; the payload never
reaches tenant or end-user surfaces. There is deliberately NO tenant-facing
twin of this endpoint: per-version win rates over a thin ledger are noise,
and noise shown to a paying user becomes a promise. If a tenant-facing
performance surface is ever wanted, it is a new, separately-reviewed
endpoint with its own honesty rules — not a relaxation of this one.

The endpoint is read-only over the Forex Signal Outcome ledger and states,
per strategy version (catalog identifier + immutable spec checksum): signal
counts, win rate, average pips, expectancy, max losing streak, period
covered — or `insufficient_data` below the documented minimum. It exists so
a human can decide whether the offline backtest/retune protocol
(forex/BACKTEST.md) is worth running. Nothing here retunes anything.

All aggregation lives in the frappe-free outcomes.report module, which an
offline harness loads by path and reuses on a ledger export — the desk
report and the harness can never disagree about what the ledger says.
"""

try:  # composed into the control product
    import frappe
except ImportError:  # standalone reuse (tests, offline harness)
    frappe = None


def _load_outcomes_module(module_name, filename):
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "outcomes", filename)
    spec = importlib.util.spec_from_file_location(module_name,
                                                  os.path.normpath(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:  # composed as a package
    from ...outcomes import ledger as _ledger
    from ...outcomes import report as _report
except (ImportError, ValueError):  # standalone: load siblings by path
    _ledger = _load_outcomes_module("rforex_outcomes_ledger", "ledger.py")
    _report = _load_outcomes_module("rforex_outcomes_report", "report.py")

ERROR_LOG_TITLE = "Forex: retraining report error"


def _require_system_manager():
    """Admin telemetry only: any caller without System Manager is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "get_forex_retraining_report is admin telemetry "
            "(System Manager only)")


def _whitelist(fn):
    return frappe.whitelist()(fn) if frappe is not None else fn


@_whitelist
def get_forex_retraining_report():
    """Observed ledger performance per immutable strategy version.

    System Manager only; read-only over the Forex Signal Outcome ledger.
    Internal errors are logged server-side and reported in-band as
    {"error": true, ...} — the endpoint itself never leaks a traceback.
    """
    _require_system_manager()
    try:
        return _report.build_report(_ledger.list_signals())
    except Exception:
        if frappe is not None:
            frappe.log_error(title=ERROR_LOG_TITLE)
        return {
            "admin_only": True,
            "error": True,
            "total_signals": 0,
            "strategies": {},
            "summary": ("report generation failed - see the Error Log "
                        "entry titled {0!r}".format(ERROR_LOG_TITLE)),
        }
