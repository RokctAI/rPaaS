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

"""Deterministic bid-pack builder - the document half of the tender module.

Given a Tender Bid's form regime, the fixture-shipped Tender Form Template
records, the bidder's Tender Business Profile and the bid's cached tender
data, this module assembles a ready-to-print preparation pack:

- every field that CAN be pre-filled is filled from the profile or the bid;
- tender-specific fields render as clearly marked USER INPUT blanks with
  kill-note-derived guidance;
- signature/initials slots render as "Sign here" / "Initial here" markers,
  or - ONLY when the caller explicitly requests a signed pack - are stamped
  with the profile's background-stripped signature images (commissioner-of-
  oaths slots are never stamped: a commissioner must sign in person);
- the pack opens with a manifest cover (fill coverage, unresolved fields)
  and, when the bid still has open fatal compliance gates, a prominent
  warning page - never a silent pass.

Everything here is pure data transformation: dict/list in, dict/HTML out.
No frappe import, no AI, no network. Database access lives in the endpoint
(api/tenders/generate_bid_pack.py), which feeds this module plain dicts, so
the builder is unit-testable standalone.

Rendering choice: clean printable HTML (A4 print CSS, one form per page)
rather than server-side PDF - wkhtmltopdf availability on composed benches
is not verifiable at compose time, and browsers print this HTML to PDF
losslessly. The output is a single self-contained HTML document.

IMPORTANT product framing baked into the output: SA tender rules forbid
retyped/substituted forms at about a third of buyers, so the pack is a
preparation worksheet mirroring each official form field-for-field - the
user transcribes onto (or checks against) the OFFICIAL issued forms. Every
page carries that warning.
"""

import html as _html

# Preference-framework conflict lint (findings F-12) - a pure, frappe-free
# sibling module. The relative import works on a composed bench; the
# importlib fallback keeps this module importable standalone by file path
# (the F-09 usage mode), still with no frappe, AI or network anywhere.
try:
	from .compliance.preference_frameworks import preference_framework_conflict
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_preference_frameworks",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)),
			"compliance",
			"preference_frameworks.py",
		),
	)
	_module = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_module)
	preference_framework_conflict = _module.preference_framework_conflict

SOURCE_PROFILE = "Profile Field"
SOURCE_BID = "Bid Field"
SOURCE_USER = "User Input"
SOURCE_SIGNATURE = "Signature"

ROLE_SIGNATORY = "Signatory"
ROLE_WITNESS_1 = "Witness 1"
ROLE_WITNESS_2 = "Witness 2"
ROLE_COMMISSIONER = "Commissioner of Oaths"

SIGNATURE_PROVENANCE = "stamped from uploaded scan"

OFFICIAL_FORMS_WARNING = (
	"Complete the OFFICIAL forms issued in the tender pack - never retype or "
	"substitute them (an explicit disqualifier at about a third of buyers). "
	"This pack mirrors each form field-for-field so you can transcribe values "
	"onto, and check them against, the official forms."
)

DIRECTOR_COLUMNS = (
	("full_name", "Full Name"),
	("id_number", "ID Number"),
	("position", "Position"),
	("tax_reference_no", "Tax Reference No"),
	("in_state_service", "In State Service"),
	("persal_number", "Persal Number"),
)

PRICING_COLUMNS = (
	("item", "Item"),
	("description", "Description"),
	("qty", "Qty"),
	("uom", "Unit"),
	("rate", "Rate (R)"),
	("amount", "Amount (R)"),
)

# List-valued auto-fill fields render as tables with these column specs.
TABLE_COLUMNS = {
	"directors": DIRECTOR_COLUMNS,
	"pricing_lines": PRICING_COLUMNS,
}


def esc(value):
	"""HTML-escapes a value for safe embedding."""
	return _html.escape(str(value), quote=True)


def is_filled(value):
	"""True when an auto-fill value is actually usable on a form."""
	if value is None:
		return False
	if isinstance(value, (list, tuple)):
		return len(value) > 0
	return bool(str(value).strip())


def resolve_field(field, profile, bid_ctx):
	"""Resolves one template field row against the profile and bid context.

	Returns the row dict extended with ``value`` and ``filled``. Signature
	rows never carry a value - stamping is a rendering concern.
	"""
	source_type = field.get("source_type")
	source_field = field.get("source_field") or ""
	value = None
	if source_type == SOURCE_PROFILE:
		value = (profile or {}).get(source_field)
	elif source_type == SOURCE_BID:
		value = (bid_ctx or {}).get(source_field)

	return {
		"section": field.get("section") or "",
		"field_label": field.get("field_label") or "",
		"source_type": source_type,
		"source_field": source_field,
		"signature_role": field.get("signature_role") or ROLE_SIGNATORY,
		"multiline": bool(field.get("multiline")),
		"guidance": field.get("guidance") or "",
		"value": value,
		"filled": is_filled(value) if source_type in (SOURCE_PROFILE, SOURCE_BID) else False,
	}


def build_form(requirement, template, profile, bid_ctx):
	"""Builds one form entry: resolved fields plus per-form fill accounting.

	``requirement`` is the regime's Tender Form Requirement row (form_code,
	form_name, mandatory, kill_note); ``template`` is the matching Tender
	Form Template as a dict with a ``fields_table`` list, or None when no
	template exists for the code (the form still gets a guided worksheet
	page driven by the requirement's kill note alone).
	"""
	fields = [
		resolve_field(field, profile, bid_ctx)
		for field in (template or {}).get("fields_table") or []
	]

	auto = [f for f in fields if f["source_type"] in (SOURCE_PROFILE, SOURCE_BID)]
	auto_filled = [f for f in auto if f["filled"]]
	user_input = [f["field_label"] for f in fields if f["source_type"] == SOURCE_USER]
	missing_auto = [f["field_label"] for f in auto if not f["filled"]]

	return {
		"form_code": requirement.get("form_code"),
		"form_name": (template or {}).get("form_title")
		or requirement.get("form_name")
		or requirement.get("form_code"),
		"mandatory": bool(requirement.get("mandatory")),
		"kill_note": requirement.get("kill_note") or "",
		"instructions": (template or {}).get("instructions") or "",
		"guide_ref": (template or {}).get("guide_ref") or "",
		"initial_every_page": bool((template or {}).get("initial_every_page")),
		"has_template": template is not None,
		"fields": fields,
		"auto_total": len(auto),
		"auto_filled": len(auto_filled),
		"user_input": user_input,
		"missing_auto": missing_auto,
	}


def build_pack(regime, templates_by_code, profile, bid_ctx, gate_failures, signing=None):
	"""Assembles the full pack: ordered forms + manifest. Pure data in/out."""
	signing = signing or {}
	forms = [
		build_form(requirement, templates_by_code.get(requirement.get("form_code")), profile, bid_ctx)
		for requirement in regime.get("forms") or []
	]

	auto_total = sum(f["auto_total"] for f in forms)
	auto_filled = sum(f["auto_filled"] for f in forms)
	coverage_pct = round(auto_filled / auto_total * 100.0, 1) if auto_total else 100.0
	missing_auto = sorted({label for f in forms for label in f["missing_auto"]})

	warnings = [OFFICIAL_FORMS_WARNING]
	if gate_failures:
		warnings.append(
			f"{len(gate_failures)} FATAL compliance gate(s) still open on this bid - "
			"submitting now risks disqualification. See the warning page."
		)
	if signing.get("sign") and signing.get("ink_warning"):
		warnings.append(signing["ink_warning"])

	# F-12 lint: when the pack's own form set signals more than one
	# preference framework (e.g. PPR 2022 specific goals alongside a
	# pre-2011 HDI equity form or a 1939-Ordinance local-content
	# certificate), warn the bid desk - only one framework scores, but
	# every framework's form must still be completed. Deterministic text
	# scan over the form names/kill notes/instructions; the fixture form
	# sets carry a single framework, so this fires only when per-pack
	# captured returnables (or desk-edited form rows) carry the signals.
	conflict = preference_framework_conflict(
		[
			text
			for form in forms
			for text in (form["form_name"], form["kill_note"], form["instructions"])
		],
		operative_system=(bid_ctx or {}).get("preference_system"),
	)
	if conflict:
		warnings.append(conflict)

	manifest = {
		"bid": bid_ctx.get("bid_name"),
		"regime": regime.get("regime_code"),
		"regime_name": regime.get("regime_name"),
		"generated_on": bid_ctx.get("generated_on"),
		"form_count": len(forms),
		"forms": [
			{
				"form_code": f["form_code"],
				"form_name": f["form_name"],
				"mandatory": f["mandatory"],
				"has_template": f["has_template"],
				"auto_total": f["auto_total"],
				"auto_filled": f["auto_filled"],
				"user_input": f["user_input"],
				"missing_auto": f["missing_auto"],
			}
			for f in forms
		],
		"fill": {
			"auto_total": auto_total,
			"auto_filled": auto_filled,
			"coverage_pct": coverage_pct,
			"user_input_total": sum(len(f["user_input"]) for f in forms),
			"missing_auto": missing_auto,
		},
		"open_fatal_gates": list(gate_failures or []),
		"signed": bool(signing.get("sign")),
		"warnings": warnings,
	}
	if signing.get("sign"):
		manifest["signature_provenance"] = SIGNATURE_PROVENANCE

	return {"manifest": manifest, "forms": forms}


# --------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------

_STYLE = """
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #111;
       margin: 0; background: #fff; }
.page { padding: 14mm 16mm; page-break-after: always; }
.page:last-child { page-break-after: auto; }
h1 { font-size: 21px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 0 0 2px; }
h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em;
     border-bottom: 1.5px solid #111; padding-bottom: 2px; margin: 14px 0 6px; }
.muted { color: #555; }
.small { font-size: 10px; }
.notice { border: 1.5px solid #111; padding: 6px 8px; margin: 8px 0;
          font-size: 10.5px; }
.kill { border: 2px solid #b00020; color: #b00020; padding: 6px 8px;
        margin: 8px 0; font-size: 10.5px; font-weight: bold; }
.warnpage { border: 4px solid #b00020; padding: 16px; }
.warnpage h2 { color: #b00020; }
.badge { display: inline-block; border: 1px solid #111; border-radius: 3px;
         padding: 0 5px; font-size: 9.5px; text-transform: uppercase;
         margin-left: 6px; vertical-align: middle; }
.badge.mand { background: #111; color: #fff; }
table.idx, table.dirs { border-collapse: collapse; width: 100%; margin: 8px 0; }
table.idx th, table.idx td, table.dirs th, table.dirs td {
  border: 1px solid #333; padding: 4px 6px; text-align: left; font-size: 11px; }
table.idx th, table.dirs th { background: #eee; }
.fieldrow { margin: 7px 0; }
.flabel { font-weight: bold; font-size: 11px; }
.fvalue { border-bottom: 1.5px dotted #444; min-height: 17px; padding: 2px 4px;
          font-size: 13px; }
.fvalue.multi { border: 1.5px dotted #444; min-height: 44px; }
.userinput { border: 2px solid #b00020; background: #fff5f5; min-height: 22px;
             padding: 3px 5px; }
.userinput.multi { min-height: 52px; }
.uimark { color: #b00020; font-weight: bold; font-size: 10px;
          text-transform: uppercase; letter-spacing: 0.04em; }
.gap { color: #8a5a00; font-weight: bold; font-size: 10px;
       text-transform: uppercase; }
.gapvalue { border-bottom: 1.5px dotted #444; background: #fff8e6;
            min-height: 17px; padding: 2px 4px; }
.guidance { font-size: 10px; color: #444; margin-top: 2px; }
.signslot { border: 2px dashed #111; min-height: 64px; margin: 6px 0;
            padding: 5px 8px; position: relative; }
.signslot .who { font-size: 10px; text-transform: uppercase; font-weight: bold; }
.signslot .mark { font-size: 13px; font-weight: bold; }
.signslot img { max-height: 52px; max-width: 240px; display: block; }
.signcaption { font-size: 10px; color: #333; }
.initials-strip { border-top: 1.5px solid #111; margin-top: 16px; padding-top: 5px;
                  display: flex; justify-content: space-between; align-items: center;
                  font-size: 10px; }
.initials-box { border: 2px dashed #111; padding: 2px 10px; min-width: 90px;
                min-height: 34px; text-align: center; }
.initials-box img { max-height: 30px; max-width: 90px; }
.stat { display: inline-block; margin-right: 22px; }
.stat .n { font-size: 24px; font-weight: bold; display: block; }
@media print { .page { padding: 8mm 6mm; } }
"""


def _render_value_cell(field):
	value = field["value"]
	if isinstance(value, (list, tuple)):
		columns = TABLE_COLUMNS.get(field["source_field"], DIRECTOR_COLUMNS)
		return _render_rows_table(value, columns)
	css = "fvalue multi" if field["multiline"] else "fvalue"
	if field["filled"]:
		return f'<div class="{css}">{esc(value)}</div>'
	if field["source_type"] == SOURCE_PROFILE:
		gap = (
			"&#9676; Not in your Business Profile - complete by hand or update "
			"the profile and regenerate"
		)
	else:
		gap = "&#9676; Not auto-filled - complete by hand from the tender pack"
	return (
		f'<div class="gap">{gap}</div>'
		f'<div class="gapvalue{" multi" if field["multiline"] else ""}">&nbsp;</div>'
	)


def _render_rows_table(rows, columns):
	head = "".join(f"<th>{esc(label)}</th>" for _key, label in columns)
	body = []
	for row in rows:
		cells = []
		for key, _label in columns:
			value = row.get(key)
			if key == "in_state_service":
				value = "YES" if value else "No"
			cells.append(f"<td>{esc(value if value is not None else '')}</td>")
		body.append("<tr>" + "".join(cells) + "</tr>")
	if not body:
		body.append(f'<tr><td colspan="{len(columns)}">&nbsp;</td></tr>')
	return f'<table class="dirs"><tr>{head}</tr>{"".join(body)}</table>'


def _render_user_input(field):
	css = "userinput multi" if field["multiline"] else "userinput"
	return (
		f'<div class="uimark">&#9658; To complete - tender-specific</div>'
		f'<div class="{css}">&nbsp;</div>'
	)


def _witness_for_role(signing, role):
	witnesses = signing.get("witnesses") or []
	index = 0 if role == ROLE_WITNESS_1 else 1
	return witnesses[index] if len(witnesses) > index else None


def _render_signature_slot(field, signing):
	role = field["signature_role"] or ROLE_SIGNATORY
	sign = bool(signing.get("sign"))

	if role == ROLE_COMMISSIONER:
		return (
			'<div class="signslot"><span class="who">Commissioner of Oaths</span>'
			'<div class="mark">Left blank - signed and stamped by the commissioner '
			"in person</div></div>"
		)

	if role in (ROLE_WITNESS_1, ROLE_WITNESS_2):
		witness = _witness_for_role(signing, role)
		caption = ""
		if witness:
			details = ", ".join(
				str(part)
				for part in (witness.get("full_name"), witness.get("id_number"), witness.get("capacity"))
				if part
			)
			caption = f'<div class="signcaption">{esc(details)}</div>'
		if sign and witness and witness.get("signature_url"):
			return (
				f'<div class="signslot"><span class="who">{esc(role)}</span>'
				f'<img src="{esc(witness["signature_url"])}" alt="{esc(role)} signature">'
				f"{caption}</div>"
			)
		return (
			f'<div class="signslot"><span class="who">{esc(role)}</span>'
			f'<div class="mark">&#10007; {esc(role)} sign here</div>{caption}</div>'
		)

	caption_parts = [
		signing.get("signatory_name"),
		signing.get("signatory_capacity"),
		signing.get("signatory_id"),
	]
	caption = ", ".join(str(part) for part in caption_parts if part)
	caption_html = f'<div class="signcaption">{esc(caption)}</div>' if caption else ""
	if sign and signing.get("signature_url"):
		return (
			f'<div class="signslot"><span class="who">Authorised Signatory</span>'
			f'<img src="{esc(signing["signature_url"])}" alt="Signature">'
			f"{caption_html}</div>"
		)
	return (
		f'<div class="signslot"><span class="who">Authorised Signatory</span>'
		f'<div class="mark">&#10007; Sign here</div>{caption_html}</div>'
	)


def _render_field(field, signing):
	if field["source_type"] == SOURCE_SIGNATURE:
		body = _render_signature_slot(field, signing)
	elif field["source_type"] == SOURCE_USER:
		body = _render_user_input(field)
	else:
		body = _render_value_cell(field)
	guidance = (
		f'<div class="guidance">{esc(field["guidance"])}</div>' if field["guidance"] else ""
	)
	return (
		f'<div class="fieldrow"><div class="flabel">{esc(field["field_label"])}</div>'
		f"{body}{guidance}</div>"
	)


def _render_initials_strip(form, signing):
	if not form["initial_every_page"]:
		return ""
	if signing.get("sign") and signing.get("initials_url"):
		box = f'<div class="initials-box"><img src="{esc(signing["initials_url"])}" alt="Initials"></div>'
	else:
		box = '<div class="initials-box">Initial here &#9656;</div>'
	return (
		'<div class="initials-strip"><span>Initial EVERY page of the official '
		"form - pack checklists audit per-page initials.</span>" + box + "</div>"
	)


def _render_form_page(form, signing):
	sections_html = []
	current_section = None
	for field in form["fields"]:
		if field["section"] != current_section:
			current_section = field["section"]
			if current_section:
				sections_html.append(f"<h3>{esc(current_section)}</h3>")
		sections_html.append(_render_field(field, signing))

	if not form["has_template"]:
		sections_html.append(
			'<div class="notice">No field template exists for this form code yet - '
			"work directly from the official form in the pack, guided by the kill "
			"note above.</div>"
		)

	mandatory_badge = (
		'<span class="badge mand">Mandatory</span>'
		if form["mandatory"]
		else '<span class="badge">Where pack includes it</span>'
	)
	kill = f'<div class="kill">KILL NOTE: {esc(form["kill_note"])}</div>' if form["kill_note"] else ""
	instructions = (
		f'<div class="notice">{esc(form["instructions"])}</div>' if form["instructions"] else ""
	)
	guide_ref = (
		f'<span class="muted small">{esc(form["guide_ref"])}</span>' if form["guide_ref"] else ""
	)

	return (
		f'<div class="page"><h2>{esc(form["form_code"])} - {esc(form["form_name"])}'
		f"{mandatory_badge}</h2>{guide_ref}{kill}{instructions}"
		f'<div class="notice small">{esc(OFFICIAL_FORMS_WARNING)}</div>'
		f"{''.join(sections_html)}{_render_initials_strip(form, signing)}</div>"
	)


def _render_cover(manifest, bid_ctx):
	fill = manifest["fill"]
	signed_line = ""
	if manifest["signed"]:
		signed_line = (
			f'<p><b>SIGNED PACK</b> - signature/initials {esc(manifest["signature_provenance"])}.</p>'
		)
	warnings_html = "".join(f'<div class="notice">{esc(w)}</div>' for w in manifest["warnings"])
	missing = fill["missing_auto"]
	missing_html = (
		"<p class='small'><b>Profile gaps:</b> " + esc("; ".join(missing)) + "</p>" if missing else ""
	)
	return (
		'<div class="page"><h1>Tender Bid Pack</h1>'
		f'<h2>{esc(bid_ctx.get("tender_title") or bid_ctx.get("tender_slug") or "")}</h2>'
		f'<p class="muted">{esc(bid_ctx.get("institution") or "")} &middot; '
		f'Closing {esc(bid_ctx.get("closing_date") or "-")} &middot; '
		f'Bid {esc(manifest.get("bid") or "")} &middot; '
		f'Regime {esc(manifest.get("regime") or "")} ({esc(manifest.get("regime_name") or "")}) '
		f'&middot; Generated {esc(manifest.get("generated_on") or "")}</p>'
		f'<div><span class="stat"><span class="n">{esc(manifest["form_count"])}</span>forms</span>'
		f'<span class="stat"><span class="n">{esc(fill["coverage_pct"])}%</span>auto-filled '
		f'({esc(fill["auto_filled"])}/{esc(fill["auto_total"])} fields)</span>'
		f'<span class="stat"><span class="n">{esc(fill["user_input_total"])}</span>'
		"fields for you to complete</span></div>"
		f"{signed_line}{warnings_html}{missing_html}</div>"
	)


def _render_gate_warning_page(manifest):
	if not manifest["open_fatal_gates"]:
		return ""
	items = "".join(f"<li>{esc(g)}</li>" for g in manifest["open_fatal_gates"])
	return (
		'<div class="page"><div class="warnpage">'
		"<h2>&#9888; OPEN FATAL COMPLIANCE GATES</h2>"
		"<p>This bid is NOT submission-ready. Each item below is a Fatal gate "
		"from the deterministic compliance layer - submitting with any of them "
		"open risks outright disqualification:</p>"
		f"<ul>{items}</ul>"
		"<p>Close every gate on the bid checklist (and file the required "
		"Compliance Artifacts), then regenerate this pack.</p></div></div>"
	)


def _render_index(manifest):
	rows = []
	for form in manifest["forms"]:
		coverage = (
			f"{form['auto_filled']}/{form['auto_total']}" if form["auto_total"] else "-"
		)
		rows.append(
			f"<tr><td>{esc(form['form_code'])}</td><td>{esc(form['form_name'])}</td>"
			f"<td>{'Mandatory' if form['mandatory'] else 'If in pack'}</td>"
			f"<td>{coverage}</td><td>{len(form['user_input'])}</td></tr>"
		)
	return (
		'<div class="page"><h2>Pack Index</h2><table class="idx">'
		"<tr><th>Form</th><th>Title</th><th>Status</th><th>Auto-filled</th>"
		"<th>To complete</th></tr>"
		f"{''.join(rows)}</table>"
		'<p class="small muted">Auto-filled counts profile/bid fields resolved '
		"from your stored data; 'To complete' counts the tender-specific fields "
		"marked in red inside each form.</p></div>"
	)


def render_pack_html(pack, bid_ctx, signing=None):
	"""Renders the assembled pack as one self-contained printable HTML doc."""
	signing = signing or {}
	manifest = pack["manifest"]
	title = f"Bid Pack - {bid_ctx.get('tender_title') or bid_ctx.get('tender_slug') or ''}"
	pages = [
		_render_cover(manifest, bid_ctx),
		_render_gate_warning_page(manifest),
		_render_index(manifest),
	]
	pages += [_render_form_page(form, signing) for form in pack["forms"]]
	return (
		"<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
		f"<title>{esc(title)}</title><style>{_STYLE}</style></head><body>"
		f"{''.join(pages)}</body></html>"
	)
