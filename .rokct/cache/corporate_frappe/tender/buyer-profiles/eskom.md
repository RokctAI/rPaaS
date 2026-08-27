# Buyer Quirk Sheet — Eskom Holdings SOC Ltd

**Buyer:** Eskom Holdings SOC Ltd (Reg No 2002/015527/30)
**Kind:** National State-Owned Enterprise (SOE) — power generation/transmission/distribution utility
**Date compiled:** 2026-08
**Packs sampled:** 10
- ocds-9t57fa-165298 (analysis JSON — Engineering design services ITT, E3342GCDLET, Lethabo)
- ocds-9t57fa-165675 (OHS Spec — Air/Flue Gas Ducts maintenance, Tutuka Power Station)
- ocds-9t57fa-165399 (OHS Spec — Boiler Refractory Service, Majuba Power Station)
- ocds-9t57fa-165234 (full ITT — Supply/Delivery/Support of Computers, E-Tendering)
- ocds-9t57fa-165940 (Publication of Bidders list — Gardening/Horticulture, Mpumalanga OU, E3224DXMPOU)
- ocds-9t57fa-164287 (OHS Spec — Boiler Pneumatic Cylinders, Kendal Power Station)
- ocds-9t57fa-165480 (Expression of Interest — Protection/Automation Schemes, Distribution, E3269DXGOU)
- ocds-9t57fa-164794 (Dual Adjudication Reporting template — Tower Assembly, NTCSA)
- ocds-9t57fa-165820 (Tender validity-extension letter, Electrification panel MWP2934DX)
- ocds-9t57fa-165240 (Tender cancellation letter, NTCSA, E2904NTCSAMWP)

Note: several sampled files (164287, 165675, 165399) are Eskom's standard OHS/SHEQ specification boilerplate attached to power-station outage contracts — they carry almost no submission/commercial content, so most of this sheet's evidentiary weight comes from the 165298 (JSON, rich extraction) and 165234 (full ITT text) packs, corroborated where possible by the EOI (165480) and the administrative letters (164794/165820/165240).

---

## Submission channel & rules

Eskom runs a **mandatory single-channel electronic** system — "Eskom E-Tendering" via the Eskom Tender Bulletin site (https://etendering.eskom.co.za). No hard-copy channel exists at all; there is no dual-channel or "hard-copy-governs" rule because paper is simply not accepted.

- ocds-9t57fa-165298: *"Failure to provide electronic copy of the tender by the deadline for tender submission will immediately render their tender nonresponsive and will be disqualified from further evaluation."* Sealing/labeling is explicitly "Not applicable — fully electronic submission; no hard copy accepted. Documents must be uploaded under specific folders: Technical, Commercial, Financial, SDL&I, Planning and Scheduling, SHEQ and other."
- ocds-9t57fa-165234: *"For E-Tendering, a tenderer's failure to have submitted/uploaded tender documents will render the tender non-responsive."* and *"For E-tendering. There will be no public opening of tenders. Tenders will be downloaded electronically."* / *"Tender Prices: Prices will not be read out."*
- ocds-9t57fa-165480 (EOI stage — same rule applies even pre-tender): *"EOI's are to be submitted electronically via Eskom E-tendering site... No Zip/condense files can be uploaded. No hard copy will be accepted."*

Resubmission rule (both ITT and EOI packs agree): only the latest uploaded version counts. ocds-9t57fa-165298: *"If a tenderer resubmits, only the latest version is considered valid and all earlier submissions become null and void; the bidder must ensure the submission status shows 'complete'."* Same wording in 165480.

File-format/size limits are standardized across packs: PDF (Excel also allowed for pricing), 500MB per document, 4GB total submission — consistent between 165298 and 165480.

## Municipal-arrears / rates clause

**Not observed in sampled packs.** None of the 10 sampled documents (including the full ITT text of 165234 and the rich JSON extraction of 165298) contain any clause about municipal rates, taxes, or arrears — a targeted search for "arrears" and "municipal rates" across all 10 files returned zero hits. This is a plausible structural feature of Eskom as a national SOE rather than a municipality (it has no municipal billing relationship to a bidder), but the sheet does not assert this as observed policy — only that the clause is absent from this sample.

## B-BBEE treatment

**Preference points only — not a hard pre-qualification gate.** Eskom uses the standard PPPFA 90/10 (contracts >R50,000,000 incl. VAT) or 80/20 (≤R50,000,000) system, and a bidder's failure to submit B-BBEE evidence costs only the points, not the bid.

- ocds-9t57fa-165298: *"Failure to submit proof of specific-goal claim is NOT disqualifying but scores 0/10 for that goal."* System confirmed as 90/10 for this >R50M engineering-design tender.
- ocds-9t57fa-165234 (line ~1018): *"A tenderer's failure to submit proof that it meets the specific goals will not result in its disqualification."* And the same file lays out the full PPPFA Regulation 2022 dual-system boilerplate (80/20 up to R50m, 90/10 above) verbatim as an annexure (lines ~2988–3265).
- Distinctive local twist: in 165298 the "Specific Goal" scored by SBD 6.1 is not a generic B-BBEE ownership/subcontracting metric but a named **graduate-placement goal** — 6 specific engineering roles (3× National Diploma Electrical, 1× ECSA-registered Graduate Professional Engineer, 1× ECSA-registered Professional Technologist/Technician, 1× SACAP-registered Draughtsman) that bidders must commit to filling with South African graduates reflective of population demographics.
- Eskom also expects the awarded contractor to *maintain or improve* its B-BBEE level for the life of the contract (165298: "bbbee_maintenance"), and expects a 1% of Contract Value CSI (Corporate Social Investment) philanthropic spend to match Eskom's own contribution — an unusual additional social-value ask layered on top of standard preference points.

## Cure/condonation policy

Eskom runs an explicit **four-tier returnables regime**, corroborated identically in both 165298 and 165234 (same boilerplate clause numbering, "Standard Conditions of Tender" 3.9–3.10), which is one of the buyer's most structurally distinctive features:

1. **Disqualifiable returnables** (required at closing, no cure) — e.g. the fully completed pricing schedule. ocds-9t57fa-165298: *"If not submitted by tender closing date and time, the tender will be disqualified."*
2. **Non-disqualifiable returnables with a cure window** — most annexures (A, B, C, D, E/F, SBD1, SBD4, SBD6.1, JV documents, the NEC3 contract). ocds-9t57fa-165234 (lines 859–886): *"if not submitted by Tender closing, or submitted with incomplete information or without a required signature, the Procurement Practitioner will, in writing, request the tenderer to submit the returnable within 5 working days. If the returnable is not completed, signed if required and/or received by the Procurement Practitioner within 5 working days of the request, the tenderer will be disqualified."* Note: the 5-working-day cure period explicitly does **not** apply to CIDB proof of grading, which has its own separate deadline (165234, line 887–888).
3. **Scored-but-not-disqualifying returnables** ("#" tier) — e.g. B-BBEE/specific-goals evidence. ocds-9t57fa-165234 (lines 889–892): *"These returnables will not be requested by the Procurement Practitioner. A tenderer that does not submit the required returnable at stipulated deadline or submits an incomplete returnable; will not be disqualified but will score zero."*
4. **Pre-award-only returnables** — CSD registration, tax compliance, financial/safety/environmental/quality Contractual Requirements. ocds-9t57fa-165298: *"Mandatory Commercial Contractual Requirement, required prior to contract award (not disqualifiable at tender closing but blocks award if unresolved)."*

This four-tier structure (immediate DQ / cure-with-deadline / score-zero-only / pre-award-gate) is more granular than a simple "curable vs fatal" binary and is worth flagging as an Eskom-specific procedural quirk.

## Security/vetting requirements

No explicit "post-award vetting" or "security clearance" process was found in the sampled packs (targeted search for "vetting" and "security clearance" returned zero hits across all 10 files). Instead, Eskom substitutes a **Supplier Integrity Pact + Integrity Declaration** regime and a POPIA-flavoured (though not POPIA-labelled) consent clause:

- ocds-9t57fa-165234: bidders must "download and read the Supplier Integrity Pact" (line 146–148) and sign an Integrity Declaration Form (Annexure D) containing this consent language (lines 2032–2041): *"I declare that I have read and understood the provisions of the Supplier Integrity Pact... I further consent that information provided in terms of this Integrity Declaration Form may be processed for verification of conflicts of interest and other ancillary purposes by Eskom. Such processing may include the sharing of the information with third parties."* — a data-processing consent functionally equivalent to a POPIA consent clause even though "POPIA" is never named in the sampled text.
- ocds-9t57fa-165298: Annexure D Integrity Declaration disqualifies for *"1. abused Eskom's procurement process (e.g. bid rigging/collusion); or 2. committed fraud or any other improper conduct in relation to such procurement process."* Directors/persons on the "Register for Tender Defaulters" or "List of Restricted Suppliers" are automatically disqualified.
- **Not observed:** formal post-award personnel security vetting (SSA-style), or explicit POPIA-named consent clauses.

## Financial demands

- **Performance security:** discretionary, not blanket. ocds-9t57fa-165234 (lines 403–417): *"Eskom reserves the right to request a Tenderer to provide Performance Bond from the tenderer before contract award. A Performance Bond of 10% of the Total contract value will be required from the Tenderer whose financial standing cannot assume the financial obligations required to render the services... The Performance Bond shall be from an institution approved by the Eskom Treasury department."* Bidders must nominate a minimum of two Eskom-approved financial institutions they could use.
- **CSD/tax compliance:** required before award, not at tender closing. ocds-9t57fa-165298: *"Proof of valid and current CSD Registration (CSD number/CSD Report)"* and a certified tax clearance certificate only for foreign tenderers with an SA footprint who are not on CSD/have no SARS PIN. ocds-9t57fa-165234 confirms: *"it is not mandatory for you to be registered on National Treasury's CSD at [tender stage]... registered on CSD prior to award."*
- **Payment terms** are value-tiered and consistent across both rich packs: contracts <R50,000,000 incl. VAT paid within 30 days of undisputed invoice; contracts ≥R50,000,000 paid within 60 days (165298 and 165234 both state this identically).
- **Audited financial statements / bank ratings:** Not observed in sampled packs.
- **Insurance requirements:** Not observed in sampled packs (the word "insurance" does not appear in any of the 10 files, including the OHS specs, which instead require a Compensation Commissioner Letter of Good Standing — see ocds-9t57fa-165399: *"The Main contractor and all his/her appointed contractors shall be registered with an appropriate employment compensation commissioner and have available a valid letter of good standing (LoG)"* — a COID/LoG requirement, not a commercial insurance policy).

## Functionality norms

- **Threshold:** 80% pass/fail, applied before price is even considered, consistent across both the engineering-design tender (165298) and the computers ITT (165234).
  - ocds-9t57fa-165298: *"Tenderers who do not meet the threshold of 80% for functionality scoring will be disqualified."*
  - ocds-9t57fa-165234: *"Phase 1 (Annexure R attached): Paper evaluation with a minimum threshold of 80%. Tenders which do not meet the Phase 1 threshold of 80% will not be evaluated for phase 2."*
- **Style:** Multi-phase, gatekeeper-first. Both packs use a binary "technical gatekeeper" pre-screen (yes/no criteria that must all pass) before any weighted scoring occurs — e.g. 165298's Phase 1 (3+ reference projects + ECSA sign-off) and 165234's gatekeeper table (local assembly/production capability, OEM/distributor certification, national footprint, demo-unit provision) plus a **Phase 2 physical verification of DEMO units** (unique to the goods/hardware tender — bidders must supply working demo laptops/desktops for physical testing, and non-compliant demo units are disqualified outright, independent of the paper score).
- Weighting in 165298 (services/design tender) heavily favours track record and staffing (Project Organisation & Resources 45%, Design Methodology 24%) over tools/cost-estimation (8%/6%).

## Distinctive kill rules / quirks

- **No public bid opening, ever, and prices never read out** — removes any competitor-pricing benchmark for bidders at any stage (165298, 165234: "Prices will not be read out").
- **Four-tier returnables cure regime** (disqualify-now / 5-day-cure / score-zero-only / pre-award-gate) — see Cure/condonation section; this granularity is unusual and worth building a compliance checklist around per-annexure.
- **Silent-CPA default trap:** if no Contract Price Adjustment (escalation) formula is submitted with the tender, pricing is locked fixed-and-firm for the entire (potentially multi-year) contract term — no opportunity to add escalation later. ocds-9t57fa-165298: *"No CPA proposal submitted = pricing deemed fixed and firm for the life of the contract."*
- **Mandatory Phase 1 binary gatekeepers independent of the weighted score** — a single "no" (e.g. missing ECSA sign-off, or failing the demo-unit/OEM-certification gate) kills the bid before functionality scoring even begins, regardless of how strong the rest of the submission is.
- **Fronting/subsidiary subcontracting discouraged and must be self-declared**: *"Main contractors/suppliers are discouraged from subcontracting with their subsidiary companies as this may be interpreted as subcontracting with themselves and/or using their subsidiaries for fronting. Where a main contractor subcontracts with a subsidiary, this must be declared in its tender documents."* (165234) — echoed in 165298.
- **100%-subcontracting is an automatic disqualifier**: *"A tenderer that sub-contracts 100% of the Scope of Work..."* triggers disqualification (165298).
- **EOI-then-closed-tender pipeline for legacy/OEM-locked equipment**: the Protection Schemes EOI (165480) is explicitly a non-binding market-testing exercise that may feed into a subsequent *closed* tender list — vendors not selected at EOI stage may never see the actual tender. Also requires signing an NDA before receiving the underlying engineering drawings needed to properly respond.
- **Dual Adjudication / Delegation of Authority machinery** is visible in the administrative packs (164794): even routine task-order modifications (extending an existing contract's completion date) go through a formal "Dual Adjudicator" sign-off with its own conflict-of-interest declaration and accept/conditionally-accept/reject outcome — evidence of a heavier internal governance layer than typical municipal buyers show in released documents.
- **Value-tiered rules recur across multiple mechanisms at the same R50,000,000 threshold**: payment terms (30 vs 60 days) and preference-point system (80/20 vs 90/10) both flip at the identical R50m mark — a bidder can predict several buyer behaviors from a single contract-value check.
- **Life-Saving Rules / zero-tolerance safety culture** on Eskom sites (from the OHS spec packs, e.g. 165399): 5 named "Life-Saving Rules" (isolate-before-touch, hook-up-at-heights, buckle-up, be-sober, permit-to-work) with a stated 0% allowable blood-alcohol level and zero-tolerance dismissal-level enforcement — unusually explicit and strict compared to typical municipal OHS boilerplate.
