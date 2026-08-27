# Requirements Checklist — DFFE-B005 26/27 (Triennial State of the Forests Report 2022–2024)

**Buyer:** National Department of Forestry, Fisheries and the Environment, 473 Steve Biko Rd, Arcadia, Pretoria · **OCDS:** ocds-9t57fa-164381
**Closing:** 2026-09-02 11:00 · **Briefing:** virtual (MS Teams), 2026-08-12 11:00 — **not compulsory**
**Contract:** 12 months from signing of MoA/SLA and issuing of the official Order
**Bid validity:** "VALID FOR ……120……DAYS FROM THE CLOSING DATE OF BID"
**Evaluation:** "Phase 1: Pre-compliance. Phase 2: Functionality Evaluation. Phase 3: Price and Preference Points."

Quoted text is from the tender pack. SDK citations use the 54-rule fixture
codes; rules-table ids in parentheses where different.

---

## 1. Phase 1 — Pre-compliance / administrative screening (quoted table)

"The bid proposal will be screened for compliance with administrative
requirements as indicated below:"

| # | Requirement (quoted standard) | SDK coverage |
|---|-------------------------------|--------------|
| 1 | Master Bid Document — "Provided and bound" | KILL-02 (KILL-RETURNABLE); binding/master-doc quirk not modelled — manual row |
| 2 | Electronic Copy (USB) — "Same as the master bid document" | KILL-25 (dual-channel: which copy governs) — manual row for the USB itself |
| 3 | SCM - SBD 1 - Invitation to Bid — "Completed and signed" | **SBD1 form template — generated in the pack** |
| 4 | B-BBEE Certificate or Sworn affidavit — "Valid B-BBEE Status Level Verification Certificate issued by SANAS, or Accredited Verification Agency, or B-BBEE Certificate issued by CIPC, or a Sworn Affidavit… together with their bids and CSD report" | GATE-BBBEE (points-only fixture; here it screens at Phase 1 — stricter than the fixture's soft-gate model) |
| 5 | Tax Compliance and CSD Registration — "CSD supplier number/ CSD registration report and/ or SARS Tax Pin" | GATE-CSD + GATE-TCS — auto-attached |
| 6 | SBD 3.3 Pricing Schedule "aligned with Annexure A – Pricing Schedule" — "Completed" | **SBD3.x form template — generated** (SDK ships a generic SBD 3.x pricing template; DFFE's Annexure A structure is not modelled) |
| 7 | SCM - SBD 4 – Bidders Disclosure — "Completed and signed" | **SBD4 form template — generated, directors table pre-filled** |
| 8 | SCM - SBD 6.1 - Preference Points Claim Form (PPR 2022) — "Completed and signed" | **SBD6.1 form template — generated** |
| 9 | Consortia/JV agreement signed by both parties, if applicable | KILL-21 model exists but is CIDB-regime-scoped — manual (N/A here: no JV) |
| 10 | Letter of Authority to sign documents — "Signed" | KILL-10 (KILL-UNSIGNED / proof of authority) |
| 11 | Consent and Indemnity Form - Annexure C — "Completed and signed" | Not modelled — buyer-authored annexure; manual row |

Buyer quirk with no fixture: "table of contents which will indicate where
each document is in the proposal" — bidder-drafted TOC, tracked manually
(it is also the guide's Master Index practice).

## 2. Phase 2 — Functionality (100 points, threshold 75%)

Quote: "The bidder must score a minimum of 75% during Phase 2
(functionality) of the evaluation to qualify for Phase 3 of the evaluation
where only points for price and preference points will be considered."
→ KILL-11 / SCORE-FUNCTIONALITY (SCORE-FUNC-THRESH). Threshold and
self-score recorded on the Tender Bid; the elimination gate is enforced by
`passes_functionality`.

| # | Criterion | Weight | Scoring indicators (abridged from pack) |
|---|-----------|--------|------------------------------------------|
| 1 | Proposed project plan, methodology and project management | 10 | Six required subheadings (Structured Work Breakdown; Objectives; Milestones and Deliverables; Timeframes; Resource Allocation; Risk Management Approach): all six = 5, five = 4, four = 3, fewer = 0 |
| 2 | Qualification of Project Team Leader (Forestry/Environmental Sciences/Natural Resources Management) | 20 | "Master's degree qualification(s) (NQF 9) and above" = 5; NQF 8 = 4; below/none = 0 |
| 3 | Experience of Project Team Leader in compiling and publishing Forestry/Environment reports (CV + contactable references) | 15 | 7+ yrs = 5; 6–7 = 4; 5–6 = 3; 4–5 = 2; 3–4 = 1; <3 = 0 |
| 4 | Qualification of Project Team Member (Social Science/Environmental Economics/Economics/Agricultural Economics) | 15 | NQF 8+ = 5; NQF 7 = 4; NQF 6 = 3; NQF 5 = 2; below = 0 |
| 5 | Experience of Team Member (data collection, analysis, report compilation, editing, design, layout, publishing; 3 contactable references) | 15 | 5+ yrs = 5; 4–5 = 4; 3–4 = 3; 2–3 = 2; 1–2 = 1; <1 = 0 |
| 6 | Company experience/track record in compiling and publishing Forestry/Environment reports — "signed reference letters on the client's letterhead" | 25 | 5 projects w/ 5 signed positive letters = 5 … 1 = 1; 0 = 0 |
|  | **TOTAL POINTS ON FUNCTIONALITY** | **100** | |

The per-criterion rubric itself is not modelled in the SDK (SCORE-EVIDENCE
in the rules-table covers the evidence-beats-claims principle); the sample's
scoring in `02-bid-no-bid.md` is hand-built to this matrix.

## 3. Phase 3 — Price & preference (80/20)

- "The preference point system applicable for this bid is 80/20." →
  SCORE-SYSTEM (SCORE-SYSTEM-8020); SDK classification for the R2.737m
  estimate agrees.
- Price formula: "Ps=80[1-(Pt-Pmin)/Pmin]" → SCORE-PRICE-FORMULA (identical
  arithmetic in `scoring.price_points`).
- Specific goals (max 20, quoted): "20 points: if the Bidder has more than
  50% (fifty percent) ownership by Black people, Women, or people with
  disabilities. 0 Points: for 50% and below ownership by stipulated
  categories of persons."
- To claim (quoted): "a) Submit a complete and signed SBD 6.1, b) Submit a
  valid B-BBEE Status Level Verification Certificate … or a Sworn Affidavit
  …, c) Submit CSD Registration Report or MAAA number/CSD Number." →
  SCORE-PREF-CLAIM (no proof = points "not claimed", not disqualification).
- Award: highest points, "However, a contract may be awarded to a tenderer
  that did not score the highest points by section 2(1) of the PPPFA." →
  SCORE-OBJECTIVE-CRITERIA (INFO-OBJ-OVERRIDE).

## 4. Kill rules summary

| Kill | SDK rule |
|------|----------|
| Below 75% functionality → not evaluated further | KILL-11 / SCORE-FUNCTIONALITY |
| Missing Phase 1 items (SBD forms, B-BBEE cert/affidavit, CSD, master doc + USB) → screened out | KILL-02 (KILL-RETURNABLE) |
| Late submission (2026-09-02 11:00) | KILL-01 (KILL-LATE) |
| Unsigned forms / no authority letter | KILL-10 (KILL-UNSIGNED) |
| No proof for specific goals → zero points (not disqualification) | SCORE-PREF-CLAIM |

## 5. SDK-generated compliance checklist (rule matching run for this bid)

Running SDK `rules.rule_applies` with `{regime: SBD, estimated_value:
2737000, institution: "Department of Forestry, Fisheries and the
Environment"}` attached **34 rules**: the full universal Fatal spine
(GATE-CIPC, GATE-CSD, GATE-DEFAULTERS, GATE-STATE-EMP, GATE-TCS, KILL-01 –
KILL-18, KILL-20, KILL-22 – KILL-25), Curable FORM-VALIDITY /
GATE-SUBCONTRACT / PRICE-SECURITY / PRICE-VAT, and Points-only GATE-BBBEE /
SCORE-PREF-CLAIM. No conditional rule fired — correct here: DFFE has no
sector registration, insurance or municipal-rates gate. The buyer-authored
items (master doc + USB + TOC, Annexure B CVs, Annexure C consent form) are
the manual remainder.
