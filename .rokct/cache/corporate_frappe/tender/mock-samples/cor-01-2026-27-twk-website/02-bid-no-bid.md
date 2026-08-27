# Bid / No-Bid Readout — COR 01/2026/27 (Theewaterskloof Municipal Website)

**Bidder:** Umzansi Infrastructure Group (Pty) Ltd — **FICTIONAL PROFILE FOR DEMO**
**Prepared:** 2026-08-20 · Bid record TB-2026-00044 · Regime: MBD
**Offer under preparation:** R2,179,056.00 incl VAT on an illustrative **5-year** maintenance/hosting schedule with mock 5.0% annual CPI escalation (linked quotation QTN-2026-00327; this advert's stated term runs only to 30 June 2029 — see §4) → SDK `preference_system_for_value(2179056)` = **80/20**

> **Grounding caveat:** this readout works from the advert-level registry
> record only (see `01-requirements-checklist.md`). Every verdict marked
> ASSUMED must be re-taken the day the official COR 01/2026/27 pack is
> collected — that collection is fatal gate #1 on the bid record.
>
> **Fictional capability extension:** for this ICT bid the fictional
> Umzansi profile is extended with a small **web/ICT unit** (as fictional
> as the rest of the profile): web lead **Lerato Khumalo, BSc Computer
> Science (NQF 7), 8 years**, one full-stack developer, one support
> technician; a portfolio of **three delivered public-facing websites, one
> for a municipal entity** (fictional); hosting resold on a Cape Town
> (ZA-resident) data centre with 99.9% uptime SLA back-to-back from the
> host. The SDK's Tender Business Profile has **no fields for any of
> this** — none of it appears in the generated pack (see README gap notes).

## 1. Deadline and briefing tracking

| Event | Date | Status |
|-------|------|--------|
| Briefing | Record: **none** | No KILL-15 exposure per the record — re-verify from the official pack; addenda watch on regardless (KILL-22) |
| Full bid document collection | ASAP — advert published 2026-08-14 | **OPEN fatal gate** — nothing can be finalised from the advert alone |
| Closing | **2026-09-18 12:00**, 06 Plein Street, Caledon | 29 days out — the longest runway of the four samples |
| Bid validity | Unknown (pack) — municipal norm 90–120 days | TCS PIN and B-BBEE evidence must outlive it |
| Enquiries | Mr. Joel Rasekgala, joelra@twk.gov.za, 028-214-3300 | Written only, as standard |

## 2. Administrative gates — pass/fail for Umzansi

| Item | Umzansi position | Verdict |
|------|------------------|---------|
| Full official pack obtained and parsed | Not yet collected | **OPEN** (manual fatal row; on the pack's warning page) |
| MBD 1, 4, 6.1, 8, 9 completed and signed | Pre-filled in generated pack (97.1% auto-fill); signatures pending | On track |
| Municipal rates clearance — company AND every director | Company certificate on file is >3 months old; director proofs not yet collected (3 directors) | **OPEN** (GATE-RATES fatal row; KILL-19 arrears check clean — no accounts in arrears) |
| CSD + TCS PIN + CIPC + defaulters/state-employee screens | MAAA number and PIN on profile; directors clear | PASS |
| B-BBEE certificate or sworn affidavit | Level 2 — **renewal audit under way, expiry not on file** (amber gap in the pack) | AT RISK — affidavit fallback available |
| MBD 5 + audited AFS | Not required below R10m (SDK correctly did not attach GATE-MBD5) | N/A |
| POPIA / data-protection returnable | Expected on a website/hosting bid but unconfirmed; POPIA form generated in pack as optional | VERIFY from pack |

## 3. Functionality outlook (ASSUMED 100 pts, threshold 70) — hand-built matrix

No functionality matrix exists in the grounding. The matrix below is
**entirely assumed**, modelled on typical municipal website RFPs; only the
threshold's base rate (municipal mode 70) is corpus-grounded. Fictional
self-scores:

| # | Criterion (assumed) | Weight | Umzansi position | Self-score |
|---|--------------------|--------|------------------|-----------|
| 1 | Company experience: comparable public-facing websites with references | 25 | 3 delivered sites, 1 municipal-entity (fictional portfolio) → 4/5 | **20** |
| 2 | Key personnel: web lead + developer qualifications and experience | 20 | Lerato Khumalo BSc CompSci (NQF 7), 8 yrs; full-stack developer 5 yrs → 4/5 | **16** |
| 3 | Methodology: redevelopment, content migration, go-live and maintenance plan | 20 | Full phased plan with WBS, milestones, risk approach → 5/5 | **20** |
| 4 | Hosting infrastructure: ZA data residency, security, backups, disaster recovery | 20 | Resold ZA data-centre hosting, daily backups, DR runbook — resold rather than owned → 3/5 | **12** |
| 5 | Support & maintenance SLA: response times, uptime, patching cadence | 15 | 99.9% uptime back-to-back, 4h/8h response tiers, monthly patching → 3–4/5 | **10** |
| | **Total** | **100** | | **78** |

SDK `passes_functionality(78, 70)` → **True** — the only one of the four
samples where the functionality gate **passes** and no functionality gate
string appears on the warning page. The pass is only as good as the
assumed threshold: at a DFFE-style 75 it still passes; at 80 (12.6% of
corpus packs) it fails. Re-score against the real matrix on pack receipt.

## 4. Price & preference (80/20) — modelled on the TYPICAL 5-year shape

**Per client domain knowledge, municipal website support/maintenance
tenders mostly carry a 5-YEAR maintenance term.** This specific advert
states a shorter term ("from date of appointment to 30 June 2029", ≈33
months) — but the quotation is deliberately built to the category-typical
shape so the sample illustrates what these bids normally look like: a
5-year hosting + maintenance schedule with annual CPI/CPA escalation.
Years 4–5 (and the escalation itself) are the industry-norm illustration
per the project owner, **not** advert text. All numbers are mock.

Corpus check on the norm: all four municipal website adverts in the
`/opportunities` registry bundle **hosting** into the same contract as
maintenance — this one (`-165555`), Mnquma LM `-165060` ("hosting and
maintenance of municipal website for a period of three years"),
Umzinyathi DM `-165289` ("website redesign, hosting, maintenance and
disaster recovery services for a period of thirty-six (36) months") and
Laingsburg `-164801` ("email, domain and website hosting services") — so
the hosting-inclusive scope is corpus-corroborated. The **5-year term
itself is not**: where the corpus adverts state a term it is 3 years/36
months, and no full packs exist for the category; the 5-year norm is
carried per client domain knowledge (unverified in corpus).

| Year | Monthly rate (hosting + retainer) | Months | Annual amount | Note |
|------|----------------------------------|--------|---------------|------|
| 1 | R24,900.00 (base: R6,500 hosting + R18,400 retainer) | 12 | R298,800.00 | |
| 2 | R26,145.00 | 12 | R313,740.00 | mock 5.0% CPI escalation |
| 3 | R27,452.00 | 12 | R329,424.00 | advert's stated term ends 30 Jun 2029 within this year |
| 4 | R28,825.00 | 12 | R345,900.00 | beyond this advert's term — 5-year norm illustration |
| 5 | R30,266.00 | 12 | R363,192.00 | beyond this advert's term — 5-year norm illustration |
| | **Recurring subtotal** | 60 | **R1,651,056.00** | |
| | Once-off (redevelopment R385,000 + migration/WCAG/POPIA R95,000 + training R48,000) | | R528,000.00 | |
| | **Quotation total (QTN-2026-00327)** | | **R2,179,056.00** | incl VAT |

- Worked example from SDK `price_points`: Umzansi at R2,179,056 vs a
  hypothetical lowest compliant 5-year offer of R1,905,000 scores
  **68.49 / 80**. Website support tenders draw aggressive small-agency
  pricing; every ~R23.8k above the lowest offer costs ~1 point.
- The escalating hosting/retainer stream is R1,651,056 — **76% of the
  offer** — so the recurring rates, not the once-off build, are where
  sharpening happens; a 1% cut in the base monthly rate compounds through
  all five escalated years.
- Specific goals: >50% black ownership (fictional 67%) → claim maximum
  points via signed MBD 6.1 + B-BBEE evidence + CSD report
  (SCORE-PREF-CLAIM: no proof, no points). Whether this pack awards on
  B-BBEE level or municipal-locality goals (common in WC municipalities)
  is unknown from the advert — **if locality-scored, Port Shepstone-based
  Umzansi likely scores 0** of the goal points.
- Multi-year note: whether the buyer accepts a CPI/CPA escalation clause
  (and against which index — CPI headline vs the contract price adjustment
  provisions) must be read from the official pack; if the pack demands
  firm pricing for the full term, the escalated years collapse into a
  single fixed rate and the margin risk transfers to the bidder. **The SDK
  has no term field, no escalation rule and no multi-year pricing model**
  — the whole schedule above lives in hand-built quotation lines (see
  README and top-level coverage findings).

## 5. Risk notes

1. **Advert-only visibility is the dominant risk.** Returnables, matrix,
   threshold, validity, channel — all unconfirmed. The 29-day runway is
   comfortable only if the pack is collected this week.
2. **Rates clearance is the classic municipal killer** (guide: WC
   municipalities run fatal returnable checklists — cf. Bergrivier "Non
   adherence to this checklist will invalidate your offer!"). Director
   proofs take the longest; started day one.
3. **Locality preference** could neutralise the price-competitive position
   of a KZN bidder in the Overberg; confirm the goals table before pricing
   final.
4. Umzansi's web unit is its smallest division — reference letters and
   CVs (the evidence, not the claims) decide criteria 1–2.
5. **Multi-year commitment and escalation risk.** The offer commits a
   small web unit to a recurring obligation of R1.65m across five
   escalated years (76% of the offer). If the buyer strikes the CPI
   escalation (firm pricing for the term), Year-5 delivery happens at
   Year-1 rates minus ~21% real value; if the buyer holds the advert's
   30 June 2029 end date, Years 4–5 revenue disappears and the once-off
   build must be recovered over the shorter term. Both scenarios must be
   re-priced the day the official pack states the term and the
   escalation clause — nothing in the SDK tracks either (no term field,
   no escalation rule).

## 6. Recommendation

**CONDITIONAL GO.** The only sample of the four with all quantitative
signals positive: functionality passes the (assumed) threshold with margin,
80/20 arithmetic is competitive, both open fatal gates (pack collection,
rates proofs) are curable well inside the 29-day runway, and the generated
pack shows the highest auto-fill of the set (97.1%). Proceed to collect
the official pack immediately; re-run this readout against the real
returnables list and matrix; abort only if the pack reveals a
locality-restricted goals table plus an 80 threshold.
