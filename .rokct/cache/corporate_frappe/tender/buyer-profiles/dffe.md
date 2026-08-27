# Buyer Quirk Sheet: Department of Forestry, Fisheries and the Environment (DFFE)

**Buyer:** National Department of Forestry, Fisheries and the Environment (473 Steve Biko Rd, Arcadia, Pretoria)
**Kind:** National department
**Packs sampled:** 1 — ocds-9t57fa-164381 (Triennial State of the Forests Report 2022–2024, DFFE-B005 26/27)
**Source:** [`../mock-samples/dffe-b005-26-27-state-of-forests/01-requirements-checklist.md`](../mock-samples/dffe-b005-26-27-state-of-forests/01-requirements-checklist.md)
**Date:** 2026-08

Note on sample composition: single-pack sheet — one SBD-regime professional-
services bid. "Not observed" below means silent in this one pack.

**SDK quirk rules encoded from this sheet (findings F-11):**
`QUIRK-DFFE-MASTERDOC` (Fatal) — auto-attaches via
`institution_matches: ["forestry, fisheries and the environment", "dffe"]`
in `fixtures/tender_compliance_rules.json`.

---

## Submission channel & rules

Sealed envelope endorsed with the bid number; physical submission. Closing
11:00. Briefing was **virtual (MS Teams) and not compulsory** — a rarity in
the sample set (no KILL-15 exposure on this pack).

Phase-1 administrative screening demands the pack's distinctive
**master-document trio** (→ `QUIRK-DFFE-MASTERDOC`):

- Master Bid Document — "Provided and bound"
- Electronic Copy (USB) — "Same as the master bid document" (KILL-25
  dual-channel family: which copy governs must be checked)
- a bidder-drafted "table of contents which will indicate where each
  document is in the proposal"

## Municipal-arrears / rates clause

Not applicable — national department; no rates clause in the sampled pack
(GATE-RATES correctly does not fire on the SBD regime).

## B-BBEE / preference treatment

80/20; specific goals: "20 points: if the Bidder has more than 50% (fifty
percent) ownership by Black people, Women, or people with disabilities. 0
Points: for 50% and below." B-BBEE certificate/sworn affidavit screens at
**Phase 1** — stricter than the fixture's points-only model (GATE-BBBEE);
no proof for goals = zero points, not disqualification (SCORE-PREF-CLAIM).
Award may deviate from highest points under PPPFA s2(1)
(SCORE-OBJECTIVE-CRITERIA).

## Eligibility gates

SBD 1/3.3/4/6.1 completed and signed (templates generate); CSD + SARS TCS
(GATE-CSD/GATE-TCS); consortia/JV agreement if applicable; Letter of
Authority to sign (KILL-10); buyer-authored Consent and Indemnity Form
Annexure C (no template — captured per bid, findings F-02).

## Functionality norms

**100 points, threshold 75%**, six-criterion rubric (project plan 10, team
leader qualification 20 [NQF 9+ = 5], team-leader experience 15, team
member qualification 15, team-member experience 15, company track record 25
with signed client-letterhead reference letters). "The bidder must score a
minimum of 75% during Phase 2 (functionality)" (KILL-11 /
SCORE-FUNCTIONALITY; the rubric itself is per-bid data — Sectioned
functionality rows, findings F-05).

## Distinctive kill rules / quirks

1. **Bound master document + identical USB copy + bidder-drafted table of
   contents** at Phase-1 screening — missing items are screened out
   (→ `QUIRK-DFFE-MASTERDOC`).
2. B-BBEE evidence screens at Phase 1 rather than only scoring points.
3. Company track record scored on **signed reference letters on the
   client's letterhead** — evidence-beats-claims at its starkest.
4. Non-compulsory virtual briefing (verify per pack — do not generalize).
