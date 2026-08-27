# Requirements Checklist — 8/2/RNM0614 (Construction of Mgodlwa Bridge in Ward 8)

**Buyer:** Ray Nkonyeni Local Municipality (KZN) · **OCDS:** ocds-9t57fa-164763 · Notice No 154 of 2026
**Closing:** 2026-09-08 12:00, bid box, foyer, Municipal Offices, 10 Connor Street, Port Shepstone
**Compulsory briefing:** site clarification meeting 2026-08-20 10:00, Marburg Boardroom Office, No1 Protea Road, Marburg
**Bid validity:** "valid for a period of 120 days" · Submission: original **plus ONE copy**, sealed envelope, **black ink**
**Document format:** CIDB Standard for Uniformity (T1 Tendering Procedures / T2 Returnable Documents / C1 Agreements & Contract Data / C2 Pricing–BoQ / C3 Scope) using RNM/MBD municipal form variants.

All quoted text below is from the tender pack. SDK rule citations use the
54-rule fixture codes (`fixtures/tender_compliance_rules.json`); where the
65-row research table (`tender/rules-table.csv`) uses a different id it is
shown in parentheses.

---

## 1. Eligibility gates (pass/fail before anything is scored)

| # | Gate (quoted from pack) | SDK rule |
|---|------------------------|----------|
| G1 | "Only tenderers who are registered with the Construction Industry Development Board (CIDB) with a classification grading of **6CE or higher**, are eligible to submit a tender and will be considered for an award." | GATE-CIDB — *did not auto-attach: rule is CIDB-regime-conditional and this bid runs the MBD regime; tracked as a manual fatal row* |
| G2 | Compulsory site clarification meeting attendance (2026-08-20 10:00, Marburg). | KILL-15 (GATE-BRIEFING) |
| G3 | Joint ventures only where "the lead partner has the higher CIDB Grading" + Certificate of Authority for Joint Ventures (A3) and JV Disclosure (A15). | KILL-21 (GATE-JV) — *CIDB-regime-conditional; manual under MBD* |
| G4 | Letter of Good Standing with the Workmen's Compensation Commissioner (A2). | GATE-COIDA — *CIDB-regime-conditional; manual under MBD* |
| G5 | Tax Pin (RNM/MBD2, B2) + CSD verification (locality goals are verified against the CSD report). | GATE-TCS, GATE-CSD |
| G6 | "Qualifications obtained from outside South Africa to be accompanied by SAQA Certification." | No fixture rule — manual row |
| G7 | Procurement above R10m: Declaration (RNM/MBD 5, A17) with audited AFS. | GATE-MBD5 (GATE-MBD5-AFS) — **auto-attached** from `estimated_value_over: 10000000` with the R42.5m estimate |
| G8 | Municipal rates standing (MBD8 questionnaire covers rates arrears). | GATE-RATES / KILL-19 — **auto-attached** (MBD regime) |

## 2. Kill rules (disqualification language quoted from the pack)

| Kill rule (quoted) | SDK rule |
|--------------------|----------|
| "The original bid document plus ONE extra (01) copy must be submitted, **failure to submit one extra copy will result in disqualification**." | KILL-16 (copy count / envelope endorsement) |
| "TENDERERS MUST COMPLETE THESE DOCUMENTS / DATA SHEETS / FORMS IN **BLACK INK**" | KILL-07 (KILL-INK) |
| Functionality: "rejecting all tender offers that fail to score the minimum number of 60% (42 out of 70) of the points for quality" | KILL-11 / SCORE-FUNCTIONALITY (SCORE-FUNC-THRESH) |
| F.3.6 Grounds for rejection and disqualification: "instantly disqualify a tenderer (and his tender offer) if it is established that he engaged in corrupt or fraudulent practices." | KILL-06 (KILL-COLLUSION) |
| MBD 9: "the accompanying bid will be disqualified if this Certificate is found not to be true and complete in every respect." | KILL-06 + MBD9 form kill note |
| Fraudulent specific-goals claims: the organ of state may "disqualify the person from the bidding process", recover costs, cancel the contract. | KILL-04 (KILL-FRAUD-PREF) |
| "Failure on the part of a tenderer to submit proof or documentation required in terms of this tender to claim points for specific goals with the tender, will be interpreted to mean that preference points for specific goals are not claimed." | SCORE-PREF-CLAIM |
| Failure to submit relevant functionality information "will/or may result in zero scores." | SCORE-EVIDENCE (rules-table id; no direct SDK fixture — covered narratively by SCORE-FUNCTIONALITY guidance) |
| Late submission (closing 2026-09-08 12:00, bid box). | KILL-01 (KILL-LATE) |
| Record of Addenda (A12) must be completed. | KILL-22 (KILL-ADDENDA) |

## 3. Returnables (T2.1, quoted: "The tenderer must complete and return documents A1 to A21; B1 to B2; C1.1 and C3 as listed below as part of his/her tender submission:")

**Schedule A — incorporated documents (complete & sign, all tenderers):**

| Ref | Returnable | SDK coverage |
|-----|-----------|--------------|
| A1 | Authority To Sign Documents | KILL-10 (proof of signing authority); no field template — checklist only |
| A2 | Letter Of Good Standing, Workmen's Compensation Commissioner | GATE-COIDA artifact (manual under MBD) |
| A3 | Certificate Of Authority for Joint Ventures | KILL-21 (manual under MBD) |
| A4 | Schedule Of Work Carried Out by The Tenderer | Not modelled — buyer-authored schedule; T2.x worksheet in the CIDB overlay pack |
| A5 | Current And Recent Projects for RNM (RNM/MBD5.2) | Not modelled |
| A6 | Schedule Of Construction Plant | Not modelled |
| A7 | Schedule Of Estimated Monthly Expenditure | Not modelled |
| A8 | Monthly Expenditure – Past Experience (RNM/MBD5.1) | Not modelled |
| A9 | Details Of Key Personnel | Not modelled (feeds functionality criteria 1–2) |
| A10 | Pricing Schedule – Firm Prices (RNM/MBD3.1) | KILL-09 pricing kill; MBD3.2 template exists but MBD3.1 does not |
| A11 | Schedule Of Daywork Rates | Not modelled |
| A12 | Record Of Addenda to Tender Documents | KILL-22 |
| A13 | Company Registration Documents | GATE-CIPC (GATE-CIPC-AUTH) — auto-attached |
| A14 | Identity Documents of Shareholders/Directors/Members | GATE-CIPC evidence bundle |
| A15 | Joint Venture Disclosure Form | KILL-21 (manual) |
| A16 | Declaration Of Interest (RNM/MBD 4) | **MBD4 form template — generated in the pack, directors table pre-filled** |
| A17 | Declaration For Procurement Above R10 Million (RNM/MBD 5) | **MBD5 form template — generated; GATE-MBD5 auto-attached** |
| A18 | Declaration Of Bidder's Past SCM Practices (RNM/MBD 8) | **MBD8 form template — generated** |
| A19 | Certificate Of Independent Tender Determination (RNM/MBD 9) | **MBD9 form template — generated** |
| A20 | Form Concerning Fulfilment of The Construction Regulations | HS-PLAN (CIDB overlay pack); manual under MBD |
| A21 | Preference Points Claim Form, PPR 2022 (RNM/MBD 6.1) | **MBD6.1 form template — generated** |

**Schedule B — attached by tenderer:**

| Ref | Returnable | SDK coverage |
|-----|-----------|--------------|
| B1 | CIDB Contractor Registration Certificate | GATE-CIDB artifact (manual fatal row on this bid) |
| B2 | Tax Pin (RNM/MBD2) | **MBD2 form template — generated**; GATE-TCS auto-attached |

**Schedule C — contract documents:** C1.1 Form of Offer and Acceptance
("must be completed"), C1.2 Contract Data, C1.3 Performance Guarantee,
C1.4 OH&S Agreement, C2 Pricing Data and BoQ, C3 Scope of Work.
C1.1 is covered by the **C1.1 template in the CIDB overlay pack**
(`03-bid-pack-cidb-overlay.html`); KILL-10's unsigned-Form-of-Offer kill and
PRICE-SECURITY (performance guarantee) apply.

## 4. Evaluation method (quoted)

- **METHOD 4**: "Financial Offer, preference, and quality (functionality)
  with 80/20 Preference Points System."
- **Stage 1 — Functionality, 70 points, minimum 60% (42/70):**
  - Applicant's Expertise – Company owner — 20 pts ("Company Owner with
    National Diploma NQF6 or equivalent in Civil Engineering/built
    environment"; NQF6+ with 10 years' experience = 20)
  - Site Agent personnel — 20 pts
  - Relevant Experience — 30 pts ("demonstrated experience with respect to
    undertaking construction of roads and bridge structures to the value
    more than R10 million", past five years)
  - "Bidders must score a minimum of 60% to pass functionality evaluation."
  - Formula: PS = (So x Ap) / Ms → SCORE-FUNCTIONALITY (SCORE-FUNC-THRESH)
- **Stage 2 — Price & preference 80/20** (values up to R50,000,000 incl VAT):
  - Price: Nf = W1 x [1-(P-Pm)/Pm], W1 = 80 → SCORE-PRICE-FORMULA
  - Specific goals (20 pts) are **locality-based**, CSD report as
    verification: "Enterprise Located within the Ray Nkonyeni Local
    Municipality = 10; Enterprise Located within the Ugu District
    Municipality = 5; Enterprise Located within the KZN Province = 1."
    → SCORE-PREF-CLAIM; note GATE-LOCALITY's fixture pattern list does not
    include RNM — no auto rule for the locality quirk.

## 5. SDK-generated compliance checklist (rule matching run for this bid)

Derived by running the SDK's `rules.rule_applies` over the 54-rule fixture
with this bid's context `{regime: MBD, estimated_value: 42500000,
institution: "Ray Nkonyeni Local Municipality"}` — 37 rules attached
(Fatal first): GATE-CIPC, GATE-CSD, GATE-DEFAULTERS, **GATE-MBD5**,
**GATE-RATES**, GATE-STATE-EMP, GATE-TCS, KILL-01 – KILL-18, **KILL-19**,
KILL-20, KILL-22 – KILL-25; Curable: FORM-VALIDITY, GATE-SUBCONTRACT,
PRICE-SECURITY, PRICE-VAT; Points-only: GATE-BBBEE, SCORE-PREF-CLAIM.

Conditional rules that **correctly** attached from context: GATE-MBD5
(value > R10m), GATE-RATES and KILL-19 (MBD regime). Conditional rules this
tender needs that did **not** attach (regime-scoped to CIDB, tracked as
manual rows on the bid): GATE-CIDB, GATE-COIDA, KILL-21.
