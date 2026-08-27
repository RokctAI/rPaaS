# Sample Pack — VCW403/SECURE/25: Total Security Solution, 60 months

Vaal Central Water · SBD forms + PSIRA regime + CIDB 4 SQ PE gate on the
works section · **13 immediate-disqualification pre-qualifiers** ·
dual-section functionality at 75% each · unannounced site inspections ·
closing 2026-09-03 12:00.

Bidder in all files: **Umzansi Infrastructure Group (Pty) Ltd — FICTIONAL
PROFILE FOR DEMO** (all identifiers deliberately fake; see top-level README).

## Files and provenance

| File | What it is | Provenance |
|------|-----------|------------|
| `01-requirements-checklist.md` | The 13 pre-qualifiers, responsiveness criteria, dual-section functionality and pricing quirks parsed from the real pack, each mapped to SDK coverage (or its absence) | **MOCKED** (hand-written; pack text quoted). §6 rule-matching list is **GENERATED** by SDK `rules.rule_applies` (34 rules — none of the security/insurance/rates/CIDB conditionals fired) |
| `02-bid-no-bid.md` | Pre-qualifier scan (3 incurable fails), per-section functionality (57% / 32% vs 75%), missed regional briefing, **NO-BID** recommendation with a next-cycle re-entry plan | **MOCKED**, except the 90/10 classification and functionality FAIL verdict — **GENERATED** by SDK `scoring.py` |
| `03-bid-pack.html` | Printable pack, **SBD regime** (9 forms), 91.8% auto-fill (56/61), 41 red blanks, and a **six-gate fatal warning page** — five gates `[manual]`, one the SDK's verbatim functionality-below-threshold string | **GENERATED** — verbatim `pack_builder.py` output. Profile/bid-context/gate-string inputs **MOCKED** to the endpoint contract |
| `03-bid-pack.manifest.json` | Machine manifest | **GENERATED** (same run) |
| `04-pack-structure.md` | The four-volume compliant submission this tender would demand (documented despite the NO-BID) | **MOCKED** |
| `03-bid-pack.pdf` | Print-ready **A4 PDF render** of the generated pack (18 pages), for review/printing in submission format | **GENERATED** — direct headless-Chromium render of the SDK's HTML output, no content changes |

No pricing spreadsheet exists for this sample, honestly: the three-region
BoQ (guarding shifts, 28,806 m fencing, CCTV/APNR/biometrics) is
deliberately "not started" in the mock — an open KILL-09 gate consistent
with the NO-BID verdict — so there are no numbers to tabulate without
inventing them.

> **Submission-format note.** The render makes the pack reviewable in
> submission format, but a real submission additionally needs wet-ink
> signatures, initials on every page, and certified copies of supporting
> documents on the buyer's OFFICIAL issued forms, assembled into the
> four-volume sealed submission this tender demands. No digital render
> carries any of that.

## What this sample shows

The stress test. The SDK's universal spine and SBD form set genuinely cover
pre-qualifier 1 and the responsiveness list, and the elimination-gate logic
correctly declares the bid not submission-ready. But 9 of 13
immediate-disqualification pre-qualifiers needed hand-added manual rows:
GATE-SECTOR's buyer patterns don't include a water board, GATE-RATES is
scoped MBD-only, GATE-CIDB/GATE-COIDA are scoped CIDB-regime-only, PSSPF
has no rule at all, and the dual-section 75% thresholds, tolerance band,
supplier rotation and unannounced site inspection live entirely outside the
fixtures. This is the clearest picture of where the deterministic layer
ends and analyst work (or the next fixture round) begins.

## Company-profile returnable — not applicable to this pack

This pack never asks for a company profile. Its 13 quoted
immediate-disqualification pre-qualifiers are all specific certificates
and forms (PSIRA registrations, COIDA, PSSPF, rates clearance, CIDB
grading, insurance…), and its functionality evidence is confined to the
buyer's own returnable schedules with proof "attached to the applicable
Returnable Schedule … or … clearly referenced", else "deemed not to have
been included" — a marketing profile satisfies none of them. The generated
company-profile artifacts for the same fictional bidder live in
[`../company-profile/`](../company-profile/) — usable as unscored
supporting material only; no returnable here demands one, so nothing is
wired (consistent with this sample's NO-BID verdict).
