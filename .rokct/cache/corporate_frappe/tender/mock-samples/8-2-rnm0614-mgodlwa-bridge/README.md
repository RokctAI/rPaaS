# Sample Pack — 8/2/RNM0614: Construction of Mgodlwa Bridge in Ward 8

Ray Nkonyeni Local Municipality · CIDB 6CE gate · METHOD 4 (functionality
42/70 minimum → 80/20 with locality-based specific goals) · closing
2026-09-08 12:00.

Bidder in all files: **Umzansi Infrastructure Group (Pty) Ltd — FICTIONAL
PROFILE FOR DEMO** (all identifiers deliberately fake; see top-level README).

## Files and provenance

| File | What it is | Provenance |
|------|-----------|------------|
| `01-requirements-checklist.md` | Gates, kill rules and the A1–A21/B1–B2/C returnables parsed from the real pack, mapped to SDK fixture rules | **MOCKED** (hand-written analysis; pack text quoted verbatim). The rule-matching list in §5 is **GENERATED** by running SDK `rules.rule_applies` (37 rules attached) |
| `02-bid-no-bid.md` | Gate pass/fail, functionality outlook (55/70 = 78.6% vs 60% bar), deadline/briefing tracking, BID recommendation | **MOCKED** (hand-written), except the 80/20 classification, the 74.57-point worked price example and the functionality pass verdict, which are **GENERATED** by SDK `scoring.py` |
| `03-bid-pack.html` | The printable A4 bid-preparation pack, **MBD regime** (12 forms: MBD1, MBD4, MBD5, MBD6.1, MBD8, MBD9, MBD2, MBD3.2, MBD6.2, MBD6.4, MBD10, POPIA), 95.6% auto-fill (65/68 fields), 49 red tender-specific blanks, 3-gate fatal warning page | **GENERATED** — verbatim `pack_builder.py` output from SDK fixtures. Inputs (fictional profile, bid context, gate strings) are **MOCKED** to the endpoint's contract |
| `03-bid-pack.manifest.json` | The pack's machine manifest (fill coverage, per-form stats, open gates) | **GENERATED** (same run) |
| `03-bid-pack-cidb-overlay.html` + `.manifest.json` | Second genuine pack after flipping the bid's regime to **CIDB** (C1.1, T2.x, HS-PLAN, QC-PLAN, GCC-ACCEPT) — the workaround for the SDK's one-regime-per-bid model | **GENERATED** (same code path, regime = CIDB) |
| `04-pack-structure.md` | Physical submission assembly in the pack's own T2.1 order, envelope/copy/ink rules | **MOCKED** (hand-written per pack instructions) |
| `03-bid-pack.pdf` + `03-bid-pack-cidb-overlay.pdf` | Print-ready **A4 PDF renders** of the two generated packs (22 and 9 pages), for review/printing in submission format | **GENERATED** — direct headless-Chromium renders of the SDK's HTML output, no content changes |

No pricing spreadsheet exists for this sample, honestly: the bid carries no
priced quotation — the CIDB bills of quantities were never mocked, which is
why MBD1's total-price face field renders as the amber profile gap — so
there are no numbers to tabulate without inventing them.

> **Submission-format note.** These renders make the pack reviewable in
> submission format, but a real submission additionally needs wet-ink
> signatures, initials on every page (black ink here, per the pack), and
> certified copies of supporting documents, transcribed onto the buyer's
> OFFICIAL issued forms and delivered as the sealed original-plus-one-copy
> this pack demands. No digital render carries any of that.

## What this sample shows

The regime-collision case: a municipal CIDB pack needs the MBD declaration
spread AND the CIDB overlay forms, but a Tender Bid holds one regime. The
MBD pack genuinely covers returnables A16–A19, A21 and B2 field-for-field
(directors table, Persal columns, preference-points claim); the CIDB
overlay pack covers C1.1/T2.x/H&S. Gaps papered over by hand: buyer-authored
schedules A1–A15, the MBD1 cover form generated but absent from this pack's
returnables, and the CIDB/COIDA/JV gates needing manual fatal rows because
their fixture rules are CIDB-regime-scoped while the bid runs MBD.

## Company-profile returnable — not applicable to this pack

This pack never asks for a marketing-style company profile. Its T2.1
returnables schedule is a closed list — "The tenderer must complete and
return documents A1 to A21; B1 to B2; C1.1 and C3 as listed below as part
of his/her tender submission" — and the nearest slots are buyer-prescribed
schedule forms that a profile document cannot substitute: A4 "Schedule Of
Work Carried Out by The Tenderer" and A9 "Details Of Key Personnel"
(completed on the issued forms; the guide's "do not dismember" rule
applies). The generated company-profile artifacts for the same fictional
bidder live in [`../company-profile/`](../company-profile/) — usable as
unscored supporting material at the bid desk's discretion, but no
returnable in this pack demands one, so nothing is wired here.
