# Requirements Checklist — VCW403/SECURE/25 (Total Security Solution, 60 months)

**Buyer:** Vaal Central Water (water board, PFMA entity), 02 Mzuzu Street, Pellissier, Bloemfontein · **OCDS:** ocds-9t57fa-164580
**Closing:** 2026-09-03 12:00 — sealed envelope; "Late submissions will not be considered"; public opening
**Compulsory briefings (regional):** Head Office, Bloemfontein, 2026-08-12 11:00 (Section 1); Vaal Gamagara Water Treatment Works, R370 Delportshoop, Northern Cape, 2026-08-14 11:00. Quote: "Attendance at the relevant site briefing(s) is mandatory. Failure to attend the compulsory briefing session will deem the response non-Responsive."
**Bid validity:** "validity period of (120 Business days) from closing date"
**Sections:** 1 — Comprehensive Physical Guarding Services (Performance & Attendance Management System); 2 — Supply, installation, maintenance, centralized monitoring incl. manning of control room/s, perimeter security fencing and related works.
**Evaluation:** "The evaluation process consists of three (03) main phases: Pre-Qualification, Functionality and Pricing" — plus an unannounced site-inspection phase for shortlisted bidders.

Quoted text is from the tender pack. SDK citations use the 54-rule fixture
codes; rules-table ids in parentheses where different.

---

## 1. Pre-qualifiers — quoted: "Bidders who do not adhere to those criteria listed below a PRE-QUALIFIER will be disqualified immediately"

| # | Pre-qualifier (quoted/abridged) | SDK coverage |
|---|--------------------------------|--------------|
| 1 | "Fully completed and signed Standard Bidding Documents: SBD Form 1, SBD Form 3.1, SBD Form 4, SBD Form 6.1" | **SBD1 / SBD3.x / SBD4 / SBD6.1 form templates — generated in the pack**; KILL-02 |
| 2 | "CIPC Documents Company (Certified)" + "ID Copies of Directors" | GATE-CIPC (GATE-CIPC-AUTH) — auto-attached |
| 3 | "Joint Venture/ Association Agreement (If applicable…)" | KILL-21 model is CIDB-regime-scoped — manual (N/A: sole bid) |
| 4 | "Original (or certified copy) of municipal rates clearance certificate or a certified copy of the lease agreement with the lessor's municipal rates certificate - Not older than 3 months (Vaal Central Water reserves the right to conduct physical verification of premises)" | **GATE-RATES did NOT auto-attach** — fixture scopes it MBD-only and VCW is an SBD-regime water board. Manual fatal row |
| 5 | "Price Proposal – to be completed in full … Non-submission or incomplete submission will result in disqualification." | KILL-09 (KILL-PRICE-BLANKS) |
| 6 | "Valid PSIRA Registration (Company, Certified)" | **GATE-SECTOR (GATE-SECTOR-REG) did NOT auto-attach** — its trigger pattern list contains only "department of tourism". Manual fatal row |
| 7 | "Valid PSIRA Registration (Directors / Members / Partners / Trustees – Grade B) Certified (Valid Grade B PSIRA registration certificates must be attached for all listed individuals)" | Same GATE-SECTOR gap — manual fatal row |
| 8 | "COIDA Letter of Good Standing or Letter (Certified)" | GATE-COIDA is CIDB-regime-scoped — manual under SBD |
| 9 | "Proof of payment for PSSPF for the last 3 months" (Private Security Sector Provident Fund) | No fixture rule — manual fatal row |
| 10 | CIDB: "…a contractor grading designation … for a **4 SQ PE OR HIGHER** are eligible to submit Tenders for this contract. NOTE: The PRE-QUALIFIER applies to Section 2…" (CIDB Regulations 25(1B)/25(7A)) | GATE-CIDB is CIDB-regime-scoped — manual fatal row under SBD |
| 11 | "Public Liability Insurance of minimum R 15 million" | GATE-INSURANCE exists but its buyer pattern list does not include VCW — manual fatal row (fixture severity is also Curable, this pack makes it an immediate disqualifier) |
| 12 | "Board of Directors resolution" | KILL-10 (proof of signing authority) |
| 13 | Key staff with certified PSIRA certificates: "Operations/Area Manager; Reaction Manager; Control Room Supervisor (For Section 2); Technician (Electronic Security Systems) (For Section 2)" | GATE-SECTOR gap — manual |

**Score: of the 13 pre-qualifiers, the SDK auto-covers ~4 (SBD form set,
CIPC, price-completeness, signing authority); 9 need manual rows** because
their conditional rules are regime- or buyer-pattern-scoped elsewhere, or
(PSSPF) have no fixture at all.

## 2. Responsiveness criteria (7-day clarification window)

Valid SARS TCS PIN (each JV party separately) → GATE-TCS; no SCM abuse /
prior-contract failure → KILL-14 context; not on Register of Tender
Defaulters (PRECCA 2004) → GATE-DEFAULTERS / KILL-03; **full CSD report
(not summary) compulsory** → GATE-CSD (fixture explicitly warns FULL vs
summary); Declaration of Interest clean → KILL-05; valid B-BBEE certificate
or certified sworn affidavit → GATE-BBBEE; Acceptance of Bid conditions
signed → KILL-02.

## 3. Functionality (75% per section; disqualifying)

Quote: "Potential service providers will have to achieve minimum number of
75 percent for their technical proposals before their financial proposals
and B-BBEE status are evaluated." Filing rule: "Functionality Documentation
must either be attached to the applicable Returnable Schedule as stated
below or can be bound into a separate volume and clearly referenced … If
the functionality document is not attached to the page or clearly
referenced it will be deemed not to have been included."

**Section 1** — "Bidders are required to attain 75% (251 points) on
functionality… Bidders who fail to meet the minimum threshold of 75% (251
points) shall be disqualified!" Criteria include: security equipment
(physical verification) 10; financial resource via bank statement average
balance tiers (R100k–R500k = 6 … >R1m = 20; "No bank rating is acceptable")
20; employees per PSIRA confirmation letter (51+ = 30) 30; supervisors with
PSIRA grades 15; vehicles with registration documents (21+ = 30; 0–10 = 5)
30; employment contracts + 3 itemised payslips at PSIRA sectoral salaries
36; performance & attendance software platform 20; uniform photos +
supplier PO/invoice 35; firearms permit book / competency / SABS safe 30;
locality (offices in Free State/Northern Cape; proof = rates clearance or
lease ≤ 3 months) 25.

**Section 2** — 165 points, same 75% kill: control-room proximity to VCW
Head Office (1–15 km = 30; 16 km+ = 5) 30; control-room org structure 15;
control-room employees per PSIRA letter (20+ = 40) 40; Control Room Manager
NQF6 + experience 30; financial resource 20; locality 30.

**Phase 3 site inspection** — unannounced, at the bidder's business
address, 100 points, minimum 75%: base station radio, two-way radios,
firearm permit book, PSIRA-tariff salary proof, live vehicle tracking,
branded vehicles, etc. "Bidders will be required to have a minimum of 4
(four) vehicles available for inspection… Proof of ownership/rental for the
mandatory vehicle requirement (7 vehicles) to be available during site
inspection." Section 2 adds a fully operational control room (30) and
"Last three (03) perimeter fencing projects installed in the last 36
months" (50).

SDK mapping: KILL-11 / SCORE-FUNCTIONALITY holds the threshold concept, but
the bid record carries **one** threshold/self-score pair — the dual-section
75% structure and the site-inspection phase are outside the model
(hand-tracked in `02-bid-no-bid.md`).

## 4. Price & preference

- "Bids will be evaluated based on the 80/20 or 90/10 preference point
  system in terms of the Preferential Procurement Policy Framework Act (Act
  5 of 2000) and the Preferential Procurement Regulations 2022." → SDK
  `preference_system_for_value(168000000)` = **90/10** for the 60-month
  estimate used here (SCORE-SYSTEM).
- Specific goals (90/10 column): ownership goals (Blacks, Women, Youth,
  disability) and "Located in a specific Local Area of Supply for work to
  be done" = 4 (proof: official municipal rates statement in bidder's name;
  certified IDs + CIPC/CSD for ownership) → SCORE-PREF-CLAIM; GATE-LOCALITY
  pattern list does not include VCW.
- **Tolerance band quirk (no fixture):** "The financial tolerance range for
  this bid is -20% to +20%" — prices outside the band vs the consultant
  estimate are eliminated.
- **Supplier rotation quirk (no fixture):** rotation threshold "Aggregate
  value of R250 million (inclusive of all taxes) awarded"; VCW "shall
  therefore not award to a Bidder that scores the highest points, if such
  Bidder has already exceeded the rotation threshold for bids."

## 5. Kill rules summary

| Kill | SDK rule |
|------|----------|
| Any pre-qualifier missed → "disqualified immediately" | KILL-02 + the manual gate rows above |
| Missed compulsory regional briefing → non-Responsive | KILL-15 (GATE-BRIEFING) |
| "Bidders who fail to submit the full set of bid documents in accordance with requirements will be disqualified." | KILL-02 (KILL-RETURNABLE) |
| Functionality < 75% per section → disqualified | KILL-11 / SCORE-FUNCTIONALITY |
| Site inspection < 75% → out | No fixture — manual |
| Price outside −20%/+20% band → eliminated | No fixture — manual |
| Late submission | KILL-01 (KILL-LATE) |
| Address changes must be notified to bids@vcwater.co.za | KILL-14 cure-watch context |

## 6. SDK-generated compliance checklist (rule matching run for this bid)

Running SDK `rules.rule_applies` with `{regime: SBD, estimated_value:
168000000, institution: "Vaal Central Water"}` attached **34 rules** — the
identical universal spine as the DFFE bid (GATE-CIPC/CSD/DEFAULTERS/
STATE-EMP/TCS, KILL-01–18, 20, 22–25, FORM-VALIDITY, GATE-SUBCONTRACT,
PRICE-SECURITY, PRICE-VAT, GATE-BBBEE, SCORE-PREF-CLAIM). **No security-,
insurance-, rates- or CIDB-conditional rule fired for the corpus's most
gate-heavy security tender** — the pattern-list/regime-scoping gap this
sample exists to demonstrate. All nine uncovered pre-qualifiers were added
as manual fatal rows; five of the six gates on the generated pack's warning
page are `[manual]`.
