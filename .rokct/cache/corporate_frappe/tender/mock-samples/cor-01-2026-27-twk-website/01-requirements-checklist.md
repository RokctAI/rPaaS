# Requirements Checklist — COR 01/2026/27 (Theewaterskloof Municipal Website: Support, Maintenance, Development and Hosting)

**Buyer:** Theewaterskloof Municipality, 06 Plein Street, Caledon, 7230, Western Cape (registry record spells it "Theewaterkloof") · **OCDS:** ocds-9t57fa-165555
**Closing:** 2026-09-18 12:00 · **Briefing:** record states none ("Is there a briefing session?: No")
**Contract:** "FROM DATE OF APPOINTMENT TO 30 JUNE 2029" (≈33 months if appointed late 2026). Note: per client domain knowledge, municipal website support/maintenance tenders **mostly carry a 5-year maintenance term** — the mock quotation therefore illustrates the typical 5-year CPI-escalated schedule (see `02-bid-no-bid.md` §4), while this advert's stated term is the shorter one quoted above
**Published:** 2026-08-14 · Enquiries: Mr. Joel Rasekgala, joelra@twk.gov.za, 028-214-3300

> **GROUNDING NOTICE — read first.** Unlike samples 1–3, **no full tender
> pack for this bid exists in the `/opportunities` registry** — and none of
> the four municipal website tenders in the corpus has one. The only source
> document is the advert-level eTenders registry record (~1.7KB): tender
> description, closing date/place, briefing flag, contact, and a link to the
> advert PDF (not mirrored locally). Everything quoted below is from that
> record; **everything else is DERIVED** from the SDK's MBD regime fixtures
> and the guide's municipal defaults, and is labelled as such. Collecting
> the official pack is itself the first fatal gate on this bid.

---

## 1. What the advert record states (quoted — the complete grounding)

- Description: "COR 01/2026/27 – SUPPORT, MAINTENANCE, DEVELOPMENT AND
  HOSTING OF A WEBSITE FOR THE THEEWATERSKLOOF MUNICIPALITY FROM DATE OF
  APPOINTMENT TO 30 JUNE 2029"
- Tender type: "Request for Bid(Open-Tender)" → a formal bid, not an RFQ,
  so the full municipal returnable spread applies (guide §1: judge by
  content; MBD prefix = municipal regime)
- Closing: "2026-09-18 12:00" → KILL-01 (KILL-LATE)
- Place: "06 Plein Street - Caledon" → physical submission expected;
  channel rules to be confirmed from the pack (KILL-07 / KILL-CHANNEL)
- Briefing: "No" → no KILL-15 exposure **per the record**; re-verify from
  the official pack before relying on it
- Category: "Administrative and support activities"

## 2. Expected municipal returnables (DERIVED — MBD regime defaults, not pack text)

A Western Cape local municipality running an open bid uses the MBD spread.
The SDK's MBD regime fixture generates all twelve; which optional ones this
pack actually issues must be confirmed from the official document.

| Returnable | Basis | SDK coverage |
|------------|-------|--------------|
| MBD 1 Invitation to Bid — total price on the face | MBD mandatory | **MBD1 template — generated, price pre-filled from linked quotation** |
| MBD 4 Declaration of Interest — every question, all directors | MBD mandatory | **MBD4 template — generated, directors table pre-filled** |
| MBD 6.1 Preference Points Claim (PPR 2022) | MBD mandatory | **MBD6.1 template — generated** |
| MBD 8 Past SCM Practices + MBD 9 Certificate of Independent Bid Determination | MBD mandatory | **MBD8/MBD9 templates — generated** |
| Municipal rates clearance — company AND every director | Municipal universal (guide §3; WC municipalities are strict — cf. Bergrivier/Overberg checklist quirks) | GATE-RATES (rules-table GATE-RATES) — **auto-attached under MBD** |
| No municipal account in arrears beyond the buyer's threshold | Municipal universal | KILL-19 — auto-attached under MBD |
| MBD 5 + 3 years audited AFS | Only above R10m — at the ≈R2.18m five-year offer it does **not** apply | GATE-MBD5 correctly did **not** fire (negative trigger test) |
| CSD registration + SARS TCS PIN, CIPC, defaulters register, state employees | Universal hard gates | GATE-CSD, GATE-TCS, GATE-CIPC, GATE-DEFAULTERS, GATE-STATE-EMP — auto-attached |
| B-BBEE certificate or sworn affidavit (preference evidence) | Universal points-only | GATE-BBBEE / SCORE-PREF-CLAIM |
| POPIA consent/processing returnable | **Highly likely on a website/hosting contract handling residents' personal information** — but DERIVED, not confirmed | POPIA form template generated (optional MBD form); GATE-POPIA rule did **not** fire — see §5 |

Website-specific returnables to expect from the official pack (none
modelled in the SDK — all would be manual rows): **company profile /
capability statement**, portfolio of comparable (ideally municipal)
websites, CVs of the web/hosting team, hosting infrastructure and
data-residency specification, backup/disaster-recovery and uptime SLA
commitments, security/patching regime, exit/handover terms.

Of these, the company-profile slot is now **demonstrated as satisfied by
generated output** (see `04-pack-structure.md` item 16): the designed A4
profile [`../company-profile/umzansi-company-profile-a4.pdf`](../company-profile/umzansi-company-profile-a4.pdf)
(GENERATED, designer engine) and the compliance-gated
[`../company-profile/startup-os/output/business_profile.md`](../company-profile/startup-os/output/business_profile.md)
(GENERATED, startup_os engine) — fictional Umzansi content; a real bid
substitutes the real company's profile and evidence.

## 3. Functionality (UNKNOWN — assumed threshold, clearly labelled)

The advert names no evaluation method. Corpus base rates
(`functionality-thresholds.md`, n=238): municipal buyer mode **70**, and 70
is the overall mode (52.5% of packs). The sample therefore **assumes a
70-point elimination threshold** — recorded on the bid as
`functionality_threshold: 70 (ASSUMED)` — and `02-bid-no-bid.md` hand-builds
a plausible website functionality matrix against it. Both numbers must be
replaced the day the official pack is collected. → KILL-11 /
SCORE-FUNCTIONALITY (rules-table SCORE-FUNC-THRESH).

## 4. Kill rules summary (universal spine + municipal conditionals)

| Kill | SDK rule |
|------|----------|
| Late submission (2026-09-18 12:00, Caledon) | KILL-01 (KILL-LATE) |
| Missing returnable / incomplete MBD form | KILL-02 (KILL-RETURNABLE) |
| Rates in arrears — company or any director | KILL-19 + GATE-RATES |
| Unsigned MBD 1/4/6.1/8/9 | KILL-10 (KILL-UNSIGNED) |
| Functionality below threshold (assumed 70) | KILL-11 |
| Wrong submission channel / retyped forms | KILL-07 (KILL-CHANNEL), KILL-13 (KILL-RETYPED) |
| Unpriced lines in the pricing schedule | KILL-09 (KILL-PRICE-BLANKS) |

## 5. SDK-generated compliance checklist (rule matching run for this bid)

Running SDK `rules.rule_applies` with `{regime: MBD, estimated_value:
2179056, institution: "Theewaterskloof Municipality"}` attached **36
rules**: the universal Fatal spine (GATE-CIPC, GATE-CSD, GATE-DEFAULTERS,
GATE-STATE-EMP, GATE-TCS, KILL-01 – KILL-18, KILL-20, KILL-22 – KILL-25),
the two MBD-conditional municipal rules **GATE-RATES and KILL-19** (both
fired from the regime alone — correct), Curable FORM-VALIDITY /
GATE-SUBCONTRACT / PRICE-SECURITY / PRICE-VAT, and Points-only GATE-BBBEE /
SCORE-PREF-CLAIM. GATE-MBD5 correctly stayed off below R10m.

**Notable non-fire:** GATE-POPIA did **not** attach, because its trigger is
a buyer-pattern list (SANRAL/Transnet). On a tender whose entire subject is
hosting a municipality's website — residents' personal information,
processing, breach exposure — the one POPIA rule in the fixture set is
invisible. The optional POPIA *form* still generates in the MBD pack, but
no checklist row demands it. With advert-only grounding, everything beyond
this universal spine (website spec, SLA, portfolio, the real functionality
matrix) is unmodelled and untracked.
