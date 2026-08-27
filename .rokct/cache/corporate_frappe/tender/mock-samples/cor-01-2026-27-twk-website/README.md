# Sample Pack — COR 01/2026/27: Theewaterskloof Municipal Website (Support, Maintenance, Development and Hosting to 30 June 2029)

Theewaterskloof Municipality (Western Cape) · MBD regime · closing
2026-09-18 12:00 · 80/20 · functionality threshold **ASSUMED 70**
(municipal corpus mode — see grounding notice below).

Bidder in all files: **Umzansi Infrastructure Group (Pty) Ltd — FICTIONAL
PROFILE FOR DEMO** (all identifiers deliberately fake; see top-level
README), extended for this bid with an equally fictional small web/ICT
unit described in `02-bid-no-bid.md`.

> **PRICING SHAPE.** The mock quotation (QTN-2026-00327, R2,179,056.00)
> is built to the **category-typical 5-year maintenance/hosting schedule
> with annual CPI escalation** — per client domain knowledge these
> tenders mostly carry a 5-year maintenance term, and all four municipal
> website adverts in the corpus bundle hosting into the contract. **This
> advert's own stated term runs only to 30 June 2029** (≈Years 1–3 of
> the schedule); Years 4–5 and the 5.0% escalation are the industry-norm
> illustration, clearly labelled as such in the quotation lines and in
> `02-bid-no-bid.md` §4.

> **GROUNDING NOTICE.** This is the thin-grounding sample of the set, on
> purpose kept honest: **no full tender pack exists in the registry for
> this bid** — or for any municipal website tender in the corpus (all four
> are advert-only records). The sole source is the ~1.7KB eTenders advert
> record (description, closing, place, briefing flag, contact). Documents
> 01/02/04 quote only that record and label everything else DERIVED or
> ASSUMED; obtaining the official pack is modelled as the bid's first
> fatal gate and appears verbatim on the generated pack's warning page.

## Files and provenance

| File | What it is | Provenance |
|------|-----------|------------|
| `01-requirements-checklist.md` | Advert-record quotes, DERIVED MBD returnables expectation, assumed functionality note, kill summary | **MOCKED** (hand-written; only the advert record quoted — no pack text exists). §5 rule-matching list is **GENERATED** by SDK `rules.rule_applies` (36 rules) |
| `02-bid-no-bid.md` | Gate pass/fail, hand-built ASSUMED functionality matrix **78 vs assumed 70 — PASS**, price example, CONDITIONAL GO | **MOCKED**, except 80/20 classification, the 68.49-point price example and the functionality PASS verdict — **GENERATED** by SDK `scoring.py` |
| `03-bid-pack.html` | Printable pack, **MBD regime** (12 forms: MBD1, 2, 3.2, 4, 5, 6.1, 6.2, 6.4, 8, 9, 10, POPIA), **97.1% auto-fill (66/68)** — the highest of the four samples — 49 red blanks, 2-gate warning page (pack-collection gate + GATE-RATES), MBD1 total-price face field filled from the linked quotation's illustrative **5-year CPI-escalated schedule** (8 lines, **R2,179,056.00**; the quotation line-items table itself renders only on the SBD3.x template — under MBD only the total reaches a form, an MBD-regime rendering gap) | **GENERATED** — verbatim `pack_builder.py` output. Profile/bid-context/quotation inputs **MOCKED** to the endpoint contract |
| `03-bid-pack.manifest.json` | Machine manifest | **GENERATED** (same run) |
| `04-pack-structure.md` | MBD-default assembly, explicitly ASSUMED pending the official pack | **MOCKED** |
| `03-bid-pack.pdf` | Print-ready **A4 PDF render** of the generated pack (22 pages), for review/printing in submission format | **GENERATED** — direct headless-Chromium render of the SDK's HTML output, no content changes |
| `05-pricing-schedule.xlsx` | Excel pricing schedule: the 5-year CPI-escalated hosting + maintenance grid (mock 5.0% p.a.), once-off items and the QTN-2026-00327 total (R2,179,056.00 incl VAT), with live formulas | **GENERATED for this sample set, hand-built** — NOT SDK output (the SDK has no spreadsheet export and no multi-year pricing model, which is finding F-06); all values are the fictional mock bid |

> **Submission-format note.** These files make the pack reviewable in
> submission format, but a real submission additionally needs wet-ink
> signatures, initials on every page, and certified copies of supporting
> documents on the buyer's OFFICIAL issued forms — whose exact returnables
> are themselves still unconfirmed until the official COR 01/2026/27 pack
> is collected (this sample's open fatal gate #1). No digital render
> carries any of that.

## What this sample shows

Two things the first three samples could not. First, the **conditional
municipal spine working end-to-end**: GATE-RATES and KILL-19 auto-attach
from the MBD regime alone, GATE-MBD5 correctly stays off below R10m, and
the MBD1 total-price field fills from the linked quotation. Second, what
the SDK looks like at its **input floor**: with advert-only grounding the
universal rule spine and form generation still run at full quality
(97.1%), but everything website-specific — POPIA rule (pattern-scoped, did
not fire on a data-heavy hosting tender), portfolio/hosting/SLA evidence
(no profile fields), the real functionality matrix, and the entire
**5-year CPI-escalated maintenance/hosting schedule** (the category-normal
pricing shape per client domain knowledge) — is invisible to the SDK and
carried by hand: the SDK has no contract-term field, no escalation rule
and no multi-year pricing model, so the year-by-year schedule lives in
flat hand-built quotation lines. See the top-level README coverage
findings, items 7–9.

## Company-profile returnable — satisfied by generated output

This is the sample of the set whose (derived) returnables carry a
**company profile / capability statement** slot — the class of returnable
the SDK's ICT-CAPABILITY worksheet was captured for. `04-pack-structure.md`
item 16 now shows that slot **SATISFIED** by the generated artifacts in
[`../company-profile/`](../company-profile/): the designed 4-page A4
profile PDF (GENERATED — designer engine) and the compliance-gated
`business_profile.md` from the startup_os engine's 30-document suite
(GENERATED). Both are fictional-Umzansi content; a real bid substitutes
the real company's profile and evidence, and re-checks the slot against
the official pack's wording once collected (this sample's open fatal
gate #1).
