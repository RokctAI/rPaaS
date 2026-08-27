# Buyer Quirk Sheet: Vaal Central Water

**Buyer:** Vaal Central Water (water board, PFMA entity; 02 Mzuzu Street, Pellissier, Bloemfontein)
**Kind:** Water board / PFMA schedule entity
**Packs sampled:** 1 — ocds-9t57fa-164580 (Total Security Solution, 60 months, VCW403/SECURE/25)
**Source:** [`../mock-samples/vcw403-secure-25-total-security/01-requirements-checklist.md`](../mock-samples/vcw403-secure-25-total-security/01-requirements-checklist.md)
**Date:** 2026-08

Note on sample composition: single-pack sheet — the corpus's most gate-heavy
security tender (13 named pre-qualifiers). "Not observed" below means silent
in this one pack.

**SDK quirk rules encoded from this sheet (findings F-11):**
`QUIRK-VCW-PRICEBAND` (Fatal), `QUIRK-VCW-ROTATION` (Points-only),
`QUIRK-VCW-INSPECTION` (Fatal) — all auto-attach via
`institution_matches: ["vaal central water"]` in
`fixtures/tender_compliance_rules.json`.

---

## Submission channel & rules

Sealed envelope, closing 12:00, public opening; "Late submissions will not
be considered." Compulsory **regional** briefings per section (Bloemfontein
Head Office for Section 1; Vaal Gamagara Water Treatment Works, Northern
Cape) — "Failure to attend the compulsory briefing session will deem the
response non-Responsive" (KILL-15). Address changes must be notified to
bids@vcwater.co.za. Bid validity 120 **business** days.

## Pre-qualifiers (instant disqualification)

"Bidders who do not adhere to those criteria listed below a PRE-QUALIFIER
will be disqualified immediately": SBD 1/3.1/4/6.1 fully completed and
signed; certified CIPC + director IDs; municipal rates clearance or lease +
lessor's rates certificate ≤3 months (with physical premises verification
reserved); complete price proposal; **valid PSIRA registration for the
company AND Grade B for all directors**; COIDA letter; **PSSPF proof of
payment (last 3 months)** — no fixture rule anywhere; CIDB 4 SQ PE+ for
Section 2; **public liability insurance min R15m**; board resolution;
PSIRA-certified key staff. Of 13 pre-qualifiers the SDK auto-covers ~4 —
the pattern-list/regime-scoping gap this sample exists to demonstrate.

## B-BBEE / preference treatment

90/10 at the 60-month estimate (SCORE-SYSTEM); specific goals include
ownership categories and "Located in a specific Local Area of Supply" = 4
(proof: official municipal rates statement in bidder's name; certified IDs
+ CIPC/CSD for ownership). Full CSD **report** (not summary) compulsory at
responsiveness (GATE-CSD).

## Financial demands

- **Price tolerance band (→ `QUIRK-VCW-PRICEBAND`, params
  `tolerance_pct: 20`):** "The financial tolerance range for this bid is
  -20% to +20%" — prices outside the band vs the consultant estimate are
  eliminated. No cure.
- **Supplier rotation (→ `QUIRK-VCW-ROTATION`, params
  `rotation_threshold_rand: 250000000`):** VCW "shall therefore not award
  to a Bidder that scores the highest points, if such Bidder has already
  exceeded the rotation threshold for bids" — aggregate R250m (incl. all
  taxes) awarded.
- Financial resource scored via bank-statement average-balance tiers; "No
  bank rating is acceptable."

## Functionality norms

**Dual sections, each with its own 75% kill** (findings F-05 — Sectioned
functionality): Section 1 guarding ≈335 pts ("minimum threshold of 75%
(251 points) shall be disqualified!"), Section 2 electronic
security/fencing 165 pts, same 75%. Functionality documentation must be
attached to the applicable returnable schedule or clearly referenced,
else "deemed not to have been included."

**Phase-3 unannounced site inspection (→ `QUIRK-VCW-INSPECTION`):** at the
bidder's business address, 100 points, minimum 75%; "a minimum of 4 (four)
vehicles available for inspection", "Proof of ownership/rental for the
mandatory vehicle requirement (7 vehicles) to be available during site
inspection"; Section 2 adds a fully operational control room and the last
three perimeter-fencing projects (36 months).

## Distinctive kill rules / quirks

1. **−20%/+20% price tolerance band** — out-of-band = eliminated
   (→ `QUIRK-VCW-PRICEBAND`).
2. **R250m rotation threshold** — highest score can lose the award
   (→ `QUIRK-VCW-ROTATION`).
3. **Unannounced site-inspection phase at 75%** with hard vehicle counts
   (→ `QUIRK-VCW-INSPECTION`).
4. PSSPF proof-of-payment pre-qualifier — sector-specific, no generic
   fixture; manual fatal row.
5. Per-section 75% functionality kills — one failing section eliminates
   the whole bid.
