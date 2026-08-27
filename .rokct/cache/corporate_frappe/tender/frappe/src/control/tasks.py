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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

import json
import time
import uuid

import frappe
import requests
from frappe.utils import cint, flt, now

# --- Direct eTenders OCDS ingestion (findings F-14) -------------------------
#
# The eTenders LIST endpoint (GET {base}?dateFrom=..&dateTo=..&PageNumber=..
# &PageSize=..) has unstable OFFSET pagination, verified live 2026-08-20: the
# same window returned 182 unique releases at PageSize=100 vs 149 at
# PageSize=1000 (union 234 > either pass), with duplicates within a single
# run and spurious short/empty pages - silent loss for any list-based
# ingestion. This fetcher therefore NEVER paginates the list endpoint.
#
# The reliable pattern (proven by a complete 163,321-release corpus fetch):
# ocids embed a sequential integer (ocds-9t57fa-{N}) and the single-release
# endpoint GET {base}/release/ocds-9t57fa-{N} is deterministic and complete.
# Never-published ids return a stable "{}" (~2% of the id space); a rare few
# return persistent HTTP 500 (server-side corrupt) - both classes are
# skipped. Incremental sync = fetch ids above the last known max, PLUS
# re-fetch a trailing window of recent ids, because releases are compiled
# snapshots that gain awards/amendments after first publication.

DEFAULT_ETENDERS_API_URL = "https://ocds-api.etenders.gov.za/api/OCDSReleases"
# Country fixture-pack scope (assessment plan #15): eTenders is the SA
# national portal, so the direct fetcher only runs when the configured
# tender_country is covered by the shipped SOUTH AFRICA (ZA) pack. Mirrors
# compliance/rules.py FIXTURE_PACK_COUNTRIES (canonical); duplicated here
# because this module is exec'd standalone by verify_wave3 and cannot
# import the sibling - verify_hygiene cross-checks the copies stay equal.
FIXTURE_PACK_COUNTRIES = ("South Africa", "ZA")
DEFAULT_TENDER_COUNTRY = "South Africa"
OCID_PREFIX = "ocds-9t57fa-"
RETRY_ATTEMPTS = 3  # attempts per release id before a 5xx is skipped as persistent
RETRY_BACKOFF_SECONDS = 2.0
DEFAULT_THROTTLE_SECONDS = 0.2  # polite inter-request delay; conf-overridable
EMPTY_RUN_LIMIT = 25  # consecutive never-published ids = past the current max
DEFAULT_REFETCH_WINDOW = 300  # trailing ids re-fetched each run (amendments/awards)
DEFAULT_MAX_IDS_PER_RUN = 2000  # per-run request budget (safety cap)
PROBE_SPAN = 10  # hole tolerance for the bootstrap max-id probe
BOOTSTRAP_ID_CAP = 100_000_000  # sanity ceiling for the exponential probe


def _resolve_trace_id():
	"""Resolves the trace id shared by one run's outgoing eTenders calls.

	Fleet trace convention (cf. api/opportunity_utils/fetch_remote_json and
	api/telemetry.log_api_call): reuse the inbound request's X-Trace-Id
	header when a request context exists, else mint a fresh uuid4 hex -
	scheduled runs have no inbound request, so each run gets one id that is
	stamped on every outgoing call it makes. Stub-safe: verify_wave3 execs
	this module against an in-memory frappe stub with no ``local`` or
	``get_request_header``, so any failure degrades to a generated id and
	never raises.
	"""
	try:
		header = (
			frappe.get_request_header("X-Trace-Id")
			if getattr(getattr(frappe, "local", None), "request", None)
			else None
		)
	except Exception:
		header = None
	return header or uuid.uuid4().hex


def _throttle_seconds():
	"""Inter-request delay; conf key etenders_fetch_throttle_seconds overrides."""
	return flt(frappe.conf.get("etenders_fetch_throttle_seconds", DEFAULT_THROTTLE_SECONDS))


def _get_release(base_url, release_id, trace_id=None):
	"""Fetches one single-release payload by integer id.

	Returns (status, payload): ("published", dict) for a real release,
	("unpublished", None) for the stable "{}" / 404 never-published case, and
	("error", None) once RETRY_ATTEMPTS transient or 5xx failures have been
	burned - the caller skips the id and moves on (persistent-500 ids are a
	known, stable class on this API).

	``trace_id`` is stamped on the outgoing X-Trace-Id header (Layer 12
	trace propagation); callers resolve it once per run so every call in a
	run correlates. Left None, the call resolves its own id.
	"""
	url = f"{base_url.rstrip('/')}/release/{OCID_PREFIX}{release_id}"
	headers = {"X-Trace-Id": trace_id or _resolve_trace_id()}
	for attempt in range(RETRY_ATTEMPTS):
		try:
			response = requests.get(url, timeout=30, headers=headers)
		except requests.RequestException:
			response = None
		time.sleep(_throttle_seconds())
		if response is not None and response.status_code == 200:
			try:
				payload = response.json()
			except ValueError:
				payload = None
			if isinstance(payload, dict) and payload.get("ocid"):
				return ("published", payload)
			# The API answers a stable "{}" for ids never published - not an
			# error, just a hole in the id space.
			return ("unpublished", None)
		if response is not None and response.status_code == 404:
			return ("unpublished", None)
		if attempt < RETRY_ATTEMPTS - 1:
			time.sleep(RETRY_BACKOFF_SECONDS)
	return ("error", None)


def _upsert_release(release):
	"""Inserts or updates one Raw Tender Cache row, deduped by ocid."""
	ocid = release.get("ocid")
	if not ocid:
		return "skipped"
	data = json.dumps(release)
	existing = frappe.db.get_value("Raw Tender Cache", {"ocid": ocid}, "name")
	if existing:
		frappe.db.set_value(
			"Raw Tender Cache", existing, {"data": data, "retrieved_on": now()}
		)
		return "updated"
	frappe.get_doc(
		{
			"doctype": "Raw Tender Cache",
			"ocid": ocid,
			"retrieved_on": now(),
			"data": data,
		}
	).insert(ignore_permissions=True)
	return "inserted"


def _published_near(base_url, start_id, span=PROBE_SPAN, trace_id=None):
	"""True when any id in [start_id, start_id + span) is published.

	The id space has never-published holes (~2%), so a max-id probe must
	tolerate a short run of "{}" before concluding it is past the end.
	Persistent-error ids count as published: they are real, allocated ids.
	"""
	for offset in range(span):
		status, _ = _get_release(base_url, start_id + offset, trace_id=trace_id)
		if status in ("published", "error"):
			return True
	return False


def _bootstrap_max(base_url, trace_id=None):
	"""Approximates the current max release id when no state is persisted yet.

	Exponential probe upward to bracket the max, then binary search on the
	hole-tolerant _published_near predicate. The result is a lower bound
	within PROBE_SPAN of the true max - exact enough to seed the resume
	pointer; the incremental gap scan pins the exact max from then on.
	Returns 0 when the API yields nothing at all.
	"""
	if not _published_near(base_url, 1, trace_id=trace_id):
		return 0
	lo = 1
	while _published_near(base_url, lo * 2, trace_id=trace_id):
		lo *= 2
		if lo > BOOTSTRAP_ID_CAP:
			return 0
	hi = lo * 2
	while lo + 1 < hi:
		mid = (lo + hi) // 2
		if _published_near(base_url, mid, trace_id=trace_id):
			lo = mid
		else:
			hi = mid
	return lo


def _fetch_and_cache_tenders_on_control():
	"""Directly ingests eTenders OCDS releases into Raw Tender Cache.

	Single-release id enumeration, never list pagination (findings F-14 -
	the list endpoint silently drops records). Per run:

	1. re-fetch a trailing window of recent ids below the persisted max
	   (compiled releases gain awards/amendments after first publication),
	2. scan upward from the persisted max, upserting every published release
	   (deduped by ocid), until EMPTY_RUN_LIMIT consecutive never-published
	   ids mark the end of the id space or the request budget is spent,
	3. persist the new max id on Tender Control Settings so the next run
	   fetches only the gap.

	First ever run (no persisted max): binary-search the current max and
	ingest only the trailing window - a full historical backfill is a
	deliberate operator action (raise max_ids_per_run / re-run), not an
	implicit side effect. Not registered in scheduler_events yet: callable,
	scheduling is a separate decision. Control hub only, like the sibling
	scheduled task.
	"""
	if frappe.conf.get("app_role") != "control":
		return None

	base_url = frappe.conf.get("etenders_api_url") or DEFAULT_ETENDERS_API_URL
	# One trace id per run, propagated on every outgoing eTenders call
	# (Layer 12 observability - same X-Trace-Id convention as the endpoint
	# shims and fetch_remote_json).
	trace_id = _resolve_trace_id()
	settings = frappe.get_single("Tender Control Settings")

	# plan #15 country scope: a non-SA tender_country has no shipped fixture
	# pack, and eTenders is the SA portal - never ingest it there. Unset /
	# default South Africa (and the ZA alias) behave exactly as before.
	country = str(settings.get("tender_country") or "").strip() or DEFAULT_TENDER_COUNTRY
	if country not in FIXTURE_PACK_COUNTRIES:
		return None

	last_max = cint(settings.get("last_fetched_release_id"))
	refetch_window = cint(settings.get("refetch_window_ids")) or DEFAULT_REFETCH_WINDOW
	max_ids = cint(settings.get("max_ids_per_run")) or DEFAULT_MAX_IDS_PER_RUN

	stats = {
		"fetched": 0,
		"inserted": 0,
		"updated": 0,
		"unpublished": 0,
		"errors": 0,
		"last_max_before": last_max,
		"last_max_after": last_max,
	}

	if not last_max:
		approx_max = _bootstrap_max(base_url, trace_id=trace_id)
		if not approx_max:
			return stats
		last_max = max(0, approx_max - refetch_window)
		stats["last_max_after"] = last_max
		refetch_start = last_max + 1  # the gap scan covers the window itself
	else:
		refetch_start = max(1, last_max - refetch_window + 1)

	budget = max_ids
	new_max = last_max

	def handle(release_id):
		nonlocal budget, new_max
		status, release = _get_release(base_url, release_id, trace_id=trace_id)
		stats["fetched"] += 1
		budget -= 1
		if status == "published":
			outcome = _upsert_release(release)
			if outcome in ("inserted", "updated"):
				stats[outcome] += 1
			new_max = max(new_max, release_id)
		elif status == "unpublished":
			stats["unpublished"] += 1
		else:
			stats["errors"] += 1
		return status

	# 1. trailing re-fetch of recent ids (amendments/awards land late)
	for release_id in range(refetch_start, last_max + 1):
		if budget <= 0:
			break
		handle(release_id)

	# 2. gap scan upward for new releases
	empty_run = 0
	release_id = last_max
	while budget > 0 and empty_run < EMPTY_RUN_LIMIT:
		release_id += 1
		status = handle(release_id)
		if status == "unpublished":
			empty_run += 1
		elif status == "published":
			empty_run = 0
		# "error" (persistent 5xx): skip the id - it neither extends nor
		# resets the never-published run

	# 3. persist the resume pointer
	stats["last_max_after"] = new_max
	if new_max != stats["last_max_before"]:
		frappe.db.set_single_value(
			"Tender Control Settings", "last_fetched_release_id", new_max
		)
	frappe.db.commit()
	return stats


def refresh_opportunities_cache():
	"""cron hook
	Scheduled task (daily, registered in the module manifest) to refresh the
	opportunities cache from the published GitHub catalog. The module composes
	into every bench, but only the control hub should fetch - tenant benches
	consume via the gateway - so the in-code app_role guard stays.
	"""
	if frappe.conf.get("app_role") != "control":
		return

	from {app_name}.tender.control.api.opportunity_utils import refresh_all_data

	refresh_all_data()

	# Renewal Watch ledger (approved design: "keep a ledger, not a model"):
	# every opportunities sync also appends new adverts to the renewal
	# ledger and settles open watches (confirm / miss). Additive - a
	# renewal failure must never break the cache refresh itself.
	try:
		from {app_name}.tender.control.renewal_sync import update_renewal_watches

		update_renewal_watches()
	except Exception:
		try:
			frappe.log_error(frappe.get_traceback(), "tender renewal watch sync")
		except Exception:
			pass  # best-effort logging - the hook must NEVER break the sync
