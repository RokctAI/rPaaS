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

import frappe

# Notification seam (plan #14): the relative import works on a composed
# bench; the importlib fallback keeps this module importable standalone by
# file path for the verify suites (the submission_gate.py pattern).
try:
	from ..notify import notify
except ImportError:  # standalone by-path import - load the seam directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_artifact_expiry_notify",
		_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "notify.py"),
	)
	_notify_module = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_notify_module)
	notify = _notify_module.notify


def sweep_compliance_artifacts():
	"""cron hook
	Weekly scheduled task (module manifest): recomputes every Compliance
	Artifact's Green/Amber/Expired status from its dates and emails the
	owning user about artifacts that changed to Amber or Expired - but only
	users who opted in via User.receive_tender_notifications (the opt-in
	gate now lives in the notify() seam, behaviour unchanged). Runs on the
	control hub only. Date arithmetic only, no AI.
	"""
	if frappe.conf.get("app_role") != "control":
		return

	changed_by_user = {}
	for name in frappe.get_all("Compliance Artifact", pluck="name"):
		artifact = frappe.get_doc("Compliance Artifact", name)
		new_status = artifact.compute_status()
		if new_status == artifact.status:
			continue
		artifact.db_set("status", new_status, update_modified=False)
		if new_status in ("Amber", "Expired"):
			changed_by_user.setdefault(artifact.user, []).append(
				f"{artifact.artifact_type} ({artifact.reference or artifact.name}): {new_status}"
			)

	# Through the notify() seam (plan #14): same email, same opt-in gate
	# (require_opt_in reads User.receive_tender_notifications per recipient,
	# missing-safe), same graceful degradation under the same error-log
	# title - the sendmail call site just lives in the seam now.
	for user, lines in changed_by_user.items():
		notify(
			recipients=[user],
			subject="Tender compliance documents need attention",
			message=(
				"The following standing compliance documents are expiring or "
				"expired:\n\n- " + "\n- ".join(lines)
			),
			require_opt_in=True,
			failure_log_title="Compliance Artifact Notification Failed",
		)
