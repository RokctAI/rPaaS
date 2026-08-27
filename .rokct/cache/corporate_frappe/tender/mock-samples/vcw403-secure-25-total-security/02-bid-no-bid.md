# Bid / No-Bid Readout — VCW403/SECURE/25 (Total Security Solution, 60 months)

**Bidder:** Umzansi Infrastructure Group (Pty) Ltd — **FICTIONAL PROFILE FOR DEMO** (Umzansi Secure Solutions division)
**Prepared:** 2026-08-20 · Bid record TB-2026-00043 · Regime: SBD
**Estimated 60-month value:** R168,000,000 incl VAT → SDK `preference_system_for_value(168000000)` = **90/10** (the pack prints both 80/20 and 90/10 tables; system fixes by value)

## 1. Deadline and briefing tracking

| Event | Date | Status |
|-------|------|--------|
| Compulsory briefing — Section 1, Head Office Bloemfontein | 2026-08-12 11:00 | **ATTENDED** (Thabo Radebe; register signed) — "Failure to attend the compulsory briefing session will deem the response non-Responsive" |
| Compulsory briefing — Northern Cape, Vaal Gamagara WTW, R370 Delportshoop | 2026-08-14 11:00 | **NOT ATTENDED** — Section coverage for the Northern Cape region is therefore non-Responsive; KILL-15 |
| Closing | **2026-09-03 12:00**, sealed envelope, public opening | 14 days out |
| Bid validity | 120 **Business** days from closing (extendable by 60 days' notice) | ≈ 6 calendar months — every certificate must survive it (FORM-VALIDITY: note calendar-vs-business-days trap) |

## 2. Pre-qualifier scan — "disqualified immediately" gates

| # | Pre-qualifier | Umzansi position | Verdict |
|---|---------------|------------------|---------|
| 1 | SBD 1 / 3.1 / 4 / 6.1 completed & signed | Pre-filled in generated pack | On track |
| 2 | Certified CIPC docs + director IDs | On file | PASS |
| 3 | JV agreement | N/A — sole bid | PASS |
| 4 | Municipal rates clearance / lease + lessor's rates cert, ≤ 3 months | **Not in hand** (premises leased; lessor's rates certificate not yet obtained) | **OPEN — fatal** |
| 5 | Price proposal complete in full | BoQ pricing not started (3 regions: guarding shifts, 28,806 m fencing, CCTV/APNR/biometrics lines) | OPEN — KILL-09 |
| 6 | PSIRA registration — company | Valid (fictional cert) | PASS |
| 7 | PSIRA **Grade B** — ALL directors | **Only 1 of 3 directors holds Grade B** (Radebe); Mthembu and Dube unregistered | **FAIL — cannot cure by 2026-09-03** (PSIRA grading takes months) |
| 8 | COIDA Letter of Good Standing (certified) | Current | PASS |
| 9 | PSSPF proof of payment, **last 3 months** | **Only 1 month of PSSPF payment history** (division recently migrated provident funds) | **FAIL — structurally impossible to cure before closing** |
| 10 | CIDB **4 SQ PE or higher** (Section 2) | Holds **6CE** — higher grade but wrong class: CE ≠ SQ/PE. GATE-CIDB fixture: "exact class" | **FAIL for Section 2** |
| 11 | Public liability insurance ≥ R15m | Current cover **R10m** | FAIL — curable in principle (broker endorsement) but must be certified in the bid |
| 12 | Board resolution | Drafted | On track |
| 13 | Key staff PSIRA certs (Ops Manager, Reaction Manager, Control Room Supervisor + Technician for S2) | Ops + Reaction covered; no PSIRA-certified Control Room Supervisor or Electronic Security Technician | FAIL for Section 2 |

**Three pre-qualifiers (7, 9, 10) cannot be cured inside the bid window.**
Under the pack's own words each alone means "disqualified immediately".

## 3. Functionality outlook (75% per section, disqualifying)

Hand-scored; the SDK bid record holds a single threshold/self-score pair
(75 / 55 recorded), which cannot express the dual-section structure — a
model limitation this sample surfaces.

**Section 1 (needs 251/335 = 75%):** equipment 10/10; financial resource
20/20 (avg balance > R1m); employees 140 per PSIRA letter → 30/30;
supervisors 15/15; **vehicles 9 owned → 5/30**; payslip compliance 36/36;
attendance software **leased, not owned → ~10/20**; uniforms 35/35;
firearms 30/30; **locality 0/25 (no Free State/Northern Cape office)**.
**≈ 191/335 = 57% — FAIL.**

**Section 2 (needs 75% of 165):** control room is in Durban → proximity
5/30; org structure 8/15; control-room staff ~10/40; CR manager 10/30;
financial 20/20; locality 0/30. **≈ 53/165 = 32% — FAIL.**

SDK `passes_functionality(55, 75)` → **False** (the verbatim elimination-
gate warning appears on the generated pack). Site-inspection phase (min 4
vehicles presented, proof for 7; live tracking; operational control room)
would compound the shortfall.

## 4. Price & preference notes (if gates were passable)

- 90/10: price dominance is near-total; preference max 10.
- Locality goal ("Located in a specific Local Area of Supply" = 4 points
  under 90/10, proof = municipal rates statement in bidder's name) is
  unreachable without a Free State/Northern Cape presence.
- **Tolerance band:** price outside −20%/+20% of the consultant estimate is
  eliminated — a blind 60-month price is risky without the briefing
  intelligence from BOTH regional sessions (another cost of the missed
  Northern Cape briefing).
- **Rotation:** awards stop at an aggregate R250m per supplier — irrelevant
  to Umzansi today, decisive for incumbents.

## 5. Risk notes

1. Missed Northern Cape briefing already narrows the bid; combined with
   pre-qualifiers 7/9/10 the submission would be dead on arrival.
2. PSIRA Grade B for **all** directors is a corporate-structure decision,
   not a paperwork task — 6–12 month lead time.
3. Locality: 55 functionality points (25 + 30) plus the locality preference
   goal hinge on a real Free State/Northern Cape office with a rates
   statement or lease — a market-entry investment, not a bid-window fix.
4. The unannounced site inspection means the scored capability must
   physically exist at the business address before submitting — nothing in
   this phase can be assembled after shortlisting.

## 6. Recommendation

**NO-BID.** Three immediate-disqualification pre-qualifiers are incurable
inside the window (director Grade B PSIRA, 3-month PSSPF history, CIDB
4 SQ PE for Section 2), both functionality sections self-score far below
75% (57% / 32%), and the Northern Cape compulsory briefing was missed.
Re-entry plan for the next cycle (VCW rotates suppliers): register
remaining directors for PSIRA Grade B now, keep PSSPF payments unbroken
(3-month history matures ~2026-11), lift public liability to R15m, open a
Bloemfontein satellite office with its own lease and rates statement, and
either register a 4 SQ class or pre-agree a Section 2 JV with an
electronic-security contractor (signed JV agreement before submission —
KILL-21).
