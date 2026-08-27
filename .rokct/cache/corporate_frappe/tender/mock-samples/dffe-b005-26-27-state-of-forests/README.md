# Sample Pack — DFFE-B005 26/27: Triennial State of the Forests Report 2022–2024

Department of Forestry, Fisheries and the Environment · SBD regime ·
three-phase evaluation with a 100-point functionality matrix and **75%
elimination threshold** · 80/20 · closing 2026-09-02 11:00.

Bidder in all files: **Umzansi Infrastructure Group (Pty) Ltd — FICTIONAL
PROFILE FOR DEMO** (all identifiers deliberately fake; see top-level README).

## Files and provenance

| File | What it is | Provenance |
|------|-----------|------------|
| `01-requirements-checklist.md` | Phase 1 screening table, 100-point functionality matrix, Phase 3 rules parsed from the real pack, mapped to SDK rules | **MOCKED** (hand-written; pack text quoted). §5 rule-matching list is **GENERATED** by SDK `rules.rule_applies` (34 rules) |
| `02-bid-no-bid.md` | Pre-compliance pass/fail, hand-scored functionality **73/100 vs 75% threshold — FAIL**, path-to-pass options, CONDITIONAL BID recommendation | **MOCKED**, except 80/20 classification, the 72.06-point price example and the functionality FAIL verdict — **GENERATED** by SDK `scoring.py` |
| `03-bid-pack.html` | Printable pack, **SBD regime** (9 forms: SBD1, SBD4, SBD6.1, SBD6.2, SBD3.x, SBD3.2, SBD7, POPIA, CST), **96.7% auto-fill (59/61)**, 41 red blanks, 2-gate warning page — including the SDK's verbatim functionality-below-threshold gate. This pack also shows the **pricing table render** from a linked quotation (six phase lines, R2,737,000.00) | **GENERATED** — verbatim `pack_builder.py` output. Profile/bid-context/quotation inputs **MOCKED** to the endpoint contract |
| `03-bid-pack.manifest.json` | Machine manifest | **GENERATED** (same run) |
| `04-pack-structure.md` | Master document + USB + bidder TOC assembly per the buyer's screening order | **MOCKED** |
| `03-bid-pack.pdf` | Print-ready **A4 PDF render** of the generated pack (18 pages), for review/printing in submission format | **GENERATED** — direct headless-Chromium render of the SDK's HTML output, no content changes |
| `05-pricing-schedule.xlsx` | Excel pricing schedule: the quotation's six phase lines (PH-1…PH-6, R2,737,000.00 incl VAT) laid out to the pack's Annexure A / SBD 3.3 structure, with live SUM formulas | **GENERATED for this sample set, hand-built** — NOT SDK output (the SDK has no spreadsheet export); all values are the fictional mock bid, to be re-keyed onto the OFFICIAL Annexure A |

> **Submission-format note.** These files make the pack reviewable in
> submission format, but a real submission additionally needs wet-ink
> signatures, initials on every page, and certified copies of supporting
> documents, entered on the buyer's OFFICIAL issued forms — bound into the
> master document with USB copy and bidder-drafted table of contents, in
> the sealed envelope this pack demands. No digital render carries any of
> that.

## What this sample shows

The best-case regime fit: DFFE's Phase 1 table is nearly the SDK's SBD
fixture spread item-for-item (SBD 1, 4, 6.1, 3.x all generated and
pre-filled), the functionality elimination gate fires exactly as the pack
prescribes, and the linked-quotation pricing table demonstrates the
document half at full coverage. Hand-mocked remainder: DFFE's own
Annexure A/B/C forms, the master-doc + USB + table-of-contents screening
quirk, and the 6-criterion scoring rubric itself.

## Company-profile returnable — not applicable to this pack

This pack lists no company-profile returnable. Company standing is scored
strictly through prescribed evidence: functionality criterion 6 ("Company
experience/track record … signed reference letters on the client's
letterhead", 25 points) and CVs on the buyer's own Annexure B template — a
marketing profile earns zero of those points and substitutes for none of
them. The generated company-profile artifacts for the same fictional
bidder live in [`../company-profile/`](../company-profile/) — usable as
unscored supporting material only; nothing in this pack's Phase 1 table or
functionality matrix demands one, so nothing is wired here.
