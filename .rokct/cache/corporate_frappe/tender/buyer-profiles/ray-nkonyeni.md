# Buyer Quirk Sheet: Ray Nkonyeni Local Municipality

**Buyer:** Ray Nkonyeni Local Municipality (Port Shepstone, KZN, Ugu District)
**Kind:** Municipality
**Packs sampled:** 1 — ocds-9t57fa-164763 (Construction of Mgodlwa Bridge in Ward 8, 8/2/RNM0614, Notice No 154 of 2026)
**Source:** [`../mock-samples/8-2-rnm0614-mgodlwa-bridge/01-requirements-checklist.md`](../mock-samples/8-2-rnm0614-mgodlwa-bridge/01-requirements-checklist.md)
**Date:** 2026-08

Note on sample composition: single-pack sheet — one CIDB-format municipal
works bid (T1/T2/C1–C3 Standard for Uniformity using RNM/MBD municipal form
variants). "Not observed" below means silent in this one pack, nothing more.

**SDK quirk rules encoded from this sheet (findings F-11):**
`QUIRK-RNM-INK` (Fatal), `QUIRK-RNM-LOCALITY` (Points-only) — both
auto-attach via `institution_matches: ["ray nkonyeni"]` in
`fixtures/tender_compliance_rules.json`.

---

## Submission channel & rules

Bid box in the foyer, Municipal Offices, 10 Connor Street, Port Shepstone;
closing 12:00. Sealed envelope; the pack demands the **original plus ONE
copy**: "The original bid document plus ONE extra (01) copy must be
submitted, failure to submit one extra copy will result in disqualification"
(→ `QUIRK-RNM-INK` params `copies_required: 2`; KILL-16 family).

Hard-copy formality: "TENDERERS MUST COMPLETE THESE DOCUMENTS / DATA SHEETS /
FORMS IN **BLACK INK**" (→ `QUIRK-RNM-INK`; KILL-07 family). Record of
Addenda (A12) must be completed (KILL-22).

## Municipal-arrears / rates clause

MBD8 questionnaire covers rates arrears; municipal rates standing gates the
bid (GATE-RATES / KILL-19 fire from the MBD regime). No distinctive RNM
elaboration observed in the sampled pack.

## B-BBEE / preference treatment

**Specific goals are locality-based, not B-BBEE** — the distinctive RNM
preference quirk: "Enterprise Located within the Ray Nkonyeni Local
Municipality = 10; Enterprise Located within the Ugu District Municipality
= 5; Enterprise Located within the KZN Province = 1" (20 pts, 80/20 METHOD
4), with the **CSD report as verification** (→ `QUIRK-RNM-LOCALITY` params
`goal_table`). No proof = points "not claimed", not disqualification
(SCORE-PREF-CLAIM); fraudulent claims can disqualify and cancel the
contract (KILL-04).

## Eligibility gates

CIDB grading **6CE or higher** to submit (GATE-CIDB — CIDB-regime-scoped in
the fixtures, manual fatal row on an MBD-regime bid); compulsory site
clarification meeting (KILL-15); JV lead partner must hold the higher CIDB
grading + A3/A15 JV forms (KILL-21); COIDA Letter of Good Standing (A2,
GATE-COIDA); >R10m declaration RNM/MBD5 with audited AFS — auto-attached at
the R42.5m estimate (GATE-MBD5); SAQA certification for foreign
qualifications (manual, no fixture rule).

## Functionality norms

METHOD 4, Stage 1 functionality **70 points, minimum 60% (42/70)**:
owner expertise 20 / site agent 20 / relevant experience 30; "rejecting all
tender offers that fail to score the minimum number of 60% (42 out of 70)
of the points for quality" (KILL-11 / SCORE-FUNCTIONALITY). Missing
functionality information "will/or may result in zero scores."

## Distinctive kill rules / quirks

1. **Black ink + original-plus-one-copy or disqualified** — quoted
   disqualification language for the copy count (→ `QUIRK-RNM-INK`).
2. **Locality-goal ladder 10/5/1 verified via CSD** — not B-BBEE
   (→ `QUIRK-RNM-LOCALITY`).
3. **Dual-regime pack**: MBD declaration spread AND CIDB C1.1/T2.x/H&S in
   one submission — the SDK models it as `regime: MBD` +
   `overlay_regime: CIDB` (findings F-01).
4. A1–A15 buyer-authored schedules (work history, plant, key personnel,
   daywork rates …) have no generic templates — captured per bid as custom
   returnables (findings F-02).
