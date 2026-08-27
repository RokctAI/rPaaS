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

"""Dispatch checksum / immutability ledger - the pure math and record shapes.

Plan #11 (SDK-Assessment-2026-08-24 section 5): ``dispatch_bid_pack``
REGENERATES the pack at send time, so the pack the user reviewed and the
pack the buyer received can differ if the profile or quotation changed in
between - and before this ledger nothing recorded what was actually sent
beyond ``dispatched_on``/``dispatched_to``. This module applies the forex
"published version is checksummed and frozen" discipline where it matters
most here: disputes about what was submitted, under rule families where
alterations disqualify (KILL-ALT-OFFER).

What it provides, all frappe-free, stdlib-only and standalone-testable
(``verify_dispatch_ledger.py``) - the same discipline as ``renewal.py`` /
``suitability.py``:

- **sha256 of the sent bytes, never of a re-render.** :func:`sha256_hex`
  fingerprints the EXACT attachment payloads handed to sendmail (the
  dispatched HTML and manifest JSON strings), not a fresh regeneration -
  regenerating for the hash would reintroduce the very drift the ledger
  exists to catch.
- **Append-only record building.** :func:`build_dispatch_record` turns one
  send (either tier: pack or correspondence) into a flat, deterministic
  record dict for the ``Tender Dispatch Record`` doctype - per-attachment
  fname/sha256/byte-size entries plus the pack/manifest/message digests.
  Records are only ever appended; the doctype controller refuses updates
  and deletes (ledger, not state - cf. Tender Renewal Event's
  ledger-not-model doctrine).
- **Attest-time artifact fingerprints.** The same hash extends to
  returnable artifacts: hash the file bytes at attest time
  (:func:`sha256_hex` on the file content) and later edits are detectable
  by :func:`artifact_unaltered`.

The frappe glue (File attachment of the sent bytes, doctype insert, the
never-fail guard around the whole write) lives in the endpoints; every
value it stores is computed here as a pure function of the sent bytes.
Deterministic - no AI anywhere.
"""

import hashlib

# The dispatched attachments are classified by the same fname suffixes
# dispatch_bid_pack generates them with - a deterministic rule, not a guess.
PACK_FNAME_SUFFIX = ".html"
MANIFEST_FNAME_SUFFIX = "-manifest.json"


def sha256_hex(content):
	"""Hex sha256 of ``content`` (bytes, or str encoded UTF-8).

	This is the ONLY hashing primitive in the ledger - one algorithm, one
	encoding rule, so a digest recorded today is reproducible byte-for-byte
	forever. Raises ValueError on any other type (hashing ``None`` or a
	number silently would fabricate a fingerprint of nothing).
	"""
	if isinstance(content, str):
		content = content.encode("utf-8")
	if not isinstance(content, (bytes, bytearray)):
		raise ValueError(
			f"sha256_hex needs bytes or str, got {type(content).__name__} - "
			"refusing to fingerprint a non-payload value"
		)
	return hashlib.sha256(bytes(content)).hexdigest()


def payload_size(content):
	"""Byte length of the payload as it would be hashed (str -> UTF-8)."""
	if isinstance(content, str):
		content = content.encode("utf-8")
	if not isinstance(content, (bytes, bytearray)):
		raise ValueError(
			f"payload_size needs bytes or str, got {type(content).__name__}"
		)
	return len(content)


def build_attachment_entries(attachments):
	"""Per-attachment ledger entries: ``[{fname, sha256, size_bytes}, ...]``.

	``attachments`` is the exact list handed to ``frappe.sendmail``
	(``[{"fname": ..., "fcontent": ...}, ...]``) - the entries fingerprint
	the sent bytes verbatim. None/empty (correspondence tier) -> ``[]``.
	Entry order preserves send order, so entry i describes attachment i.
	"""
	entries = []
	for attachment in attachments or []:
		entries.append(
			{
				"fname": str(attachment.get("fname") or ""),
				"sha256": sha256_hex(attachment.get("fcontent")),
				"size_bytes": payload_size(attachment.get("fcontent")),
			}
		)
	return entries


def classify_digests(entries):
	"""(pack_sha256, manifest_sha256) picked from attachment entries.

	The pack digest is the first entry whose fname ends ``.html`` (the
	dispatched pack HTML); the manifest digest the first ending
	``-manifest.json``. Either is "" when no such attachment was sent
	(correspondence tier sends none) - empty string, never a fabricated
	hash-of-nothing.
	"""
	pack_sha256 = ""
	manifest_sha256 = ""
	for entry in entries:
		fname = entry.get("fname") or ""
		if not pack_sha256 and fname.endswith(PACK_FNAME_SUFFIX):
			pack_sha256 = entry["sha256"]
		if not manifest_sha256 and fname.endswith(MANIFEST_FNAME_SUFFIX):
			manifest_sha256 = entry["sha256"]
	return pack_sha256, manifest_sha256


def build_dispatch_record(
	bid,
	mode,
	recipient,
	subject,
	message,
	dispatched_on,
	attachments=None,
	pack_signed=False,
):
	"""One append-only ledger record for one accepted send, as a plain dict.

	Pure: everything is computed from the arguments (the values actually
	handed to sendmail plus the audit timestamp the endpoint wrote) -
	nothing is re-read or regenerated. Keys map 1:1 onto the
	``Tender Dispatch Record`` doctype fields, except ``attachments``
	(the entry list from :func:`build_attachment_entries`), which the glue
	serializes to ``attachments_json`` after adding each sent file's
	stored ``file_url``.

	Both tiers are recorded: pack mode carries pack/manifest digests and
	attachment entries; correspondence mode records the message digest
	with no attachments. ``message_sha256`` fingerprints the body as sent
	in either tier ("" when there was none).
	"""
	entries = build_attachment_entries(attachments)
	pack_sha256, manifest_sha256 = classify_digests(entries)
	return {
		"bid": str(bid or ""),
		"mode": str(mode or ""),
		"recipient": str(recipient or ""),
		"subject": str(subject or ""),
		"dispatched_on": dispatched_on,
		"pack_signed": 1 if pack_signed else 0,
		"pack_sha256": pack_sha256,
		"manifest_sha256": manifest_sha256,
		"message_sha256": sha256_hex(message) if (message or "") != "" else "",
		"attachment_count": len(entries),
		"attachments": entries,
	}


def artifact_unaltered(stored_sha256, current_content):
	"""Detects later edits to an attested artifact (plan #11's extension).

	``True``/``False`` when a stored attest-time digest exists (the file's
	current bytes match / do not match the bytes the desk attested), and
	``None`` when there is no stored digest to compare against - unknown
	is reported as unknown, never as a pass (the module-wide honesty rule:
	no fabricated verdicts).
	"""
	stored = str(stored_sha256 or "").strip().lower()
	if not stored:
		return None
	return sha256_hex(current_content) == stored
