# Requirements Checklist — TENDER 18-2025/26 (Musina LM: Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System, 3 Years)

**Buyer:** Musina Local Municipality, Private Bag X611, Musina 0900, Limpopo · Tel 015-534 6100
**Closing:** **11 May 2026 @ 11:00** (pack cover and Invitation to Tender) — **ALREADY PASSED at build date 2026-08-20; retrospective sample**
**Briefing:** none anywhere in the 65-page pack — the only "compulsory" items are quarterly contract performance reviews (§5.4(d)) post-award
**Contract:** "FOR A PERIOD OF THREE YEARS" — "three (3) years/thirty-six (36) months" (ToR §1; pricing instruction §6(a)). Note: per client domain knowledge Musina terms were believed to run 5 years; **this pack's own stated term is 3 years** — recorded as pack evidence
**Enquiries (written only, "Telephonic queries/enquiries will not be entertained"):** technical — Ms. L.S Mokoena, Acting Manager: ICT, lesedim@musina.gov.za; SCM — Mrs. R.M. Siziba, Manager SCM, marys@musina.gov.za

> **GROUNDING NOTICE.** This is the **best-grounded sample of the set**: the
> complete official 65-page pack was fetched directly from the buyer's
> website (musina.gov.za download page, linked by the client) and has a full
> text layer — no OCR, no registry intermediary. Everything below quotes the
> pack itself. The one grounding caveat is temporal: the tender **closed
> 2026-05-11**, three months before this sample was built, so the sample is
> a retrospective demonstration — the closed window is rendered as a fatal
> gate on the generated pack's warning page. There is **no matching record
> in the `/opportunities` registry** (the seven Musina records there are
> unrelated 2026-2027 RFQs), so no advert metadata supplements the pack.

---

## 1. The pack's own returnables checklist (page 2, quoted)

"CHECKLIST OF DOCUMENTATION TO BE ATTACHED":

- "Tax Compliance Status Pin Issued" → GATE-TCS
- "Certified ID copies of all members / owners / directors / shareholders /
  Trustees" → manual row (no fixture rule demands certified ID copies)
- "Copy of municipal rates and taxes statement of account not older than
  three months **for all directors and for the company**" → **GATE-RATES**
  (fires from the MBD regime — matches this demand almost word-for-word)
- "Certified Copy of newest Financial Statements of company" → manual row —
  note GATE-MBD5's `estimated_value_over: 10000000` trigger correctly does
  NOT fire at the ≈R2.57m offer, yet Musina demands financials from
  **every** bidder regardless of value (and mandatory requirement 5.1(i)
  escalates it to "Recent Audited financial statements (previous 3
  financial years)") — a value-decoupled AFS demand the fixture set cannot
  express
- "Central supplier database registration report" → GATE-CSD (also CRITICAL
  CRITERIA #1: "ONLY BIDDERS WHO ARE REGISTERED ON THE CENTRAL SUPPLIER
  DATABASE WILL BE CONSIDERED FOR APPOINTMENT")
- "All other documents as indicated in the General Conditions Document"
- "NB: INITIAL EVERY PAGE OF THE TENDER DOCUMENT AT THE BOTTOM" → KILL-02 /
  the initials strip the SDK renders on every form page
- "Attach the above documentation to the back of the Tender Document.
  Failure to submi[t]…" (sentence truncated in the pack itself; §3.9 of the
  Information Brochure completes the rule: attach "at the back of the
  official bid document. (i.e. After the Councils price schedule)")

## 2. Mandatory bid requirements (§5.1, quoted — "To ensure your proposal is considered for evaluation")

These are the pack's Stage-1 pass/fail technical returnables. **None has a
fixture rule or form template** — all are manual checklist rows:

| # | Requirement (pack §5.1) | SDK coverage |
|---|-------------------------|--------------|
| a | Proposal detailing "the proposed system solution functionality that meets the minimum specifications requirement" (the (a)–(eee) spec list, §4) | none — manual |
| b | "tariff costs for the Call center Management system solution" | none — manual |
| c | "detailed project plan … with clear timelines/timeframes, outlining milestones from project inception to completion" | none — manual |
| d | "**Hand-completed and signed tender document**" | KILL-07 (ink rules) + KILL-13 (official forms only); CRITICAL CRITERIA #3 "BID DOCUMENT MUST BE COMPLETED IN INK" |
| e | "specify the system software proposed … attach a system description as proof" | none — manual |
| f | "proof of execution of similar work … at least three (3) contactable references, **and appointment letters** of a similar service … contract term/duration of at least 12 months" | none — manual (the guide's "Trinity of Evidence" pattern) |
| g | "Risk management plan associated with the project" | none — manual |
| h | "User Operational Training Plan (for all system users, system administrators, and mobile app users)" | none — manual |
| i | "Recent Audited financial statements (previous 3 financial years)" | GATE-MBD5 text matches but its >R10m trigger does not fire — manual |
| j | "**Service Provider Banking Rating [A to C] not older than 3 months**" | none — manual (rendered as a `[manual]` fatal gate on the warning page) |
| k | "Detailed pricing per price schedule" | KILL-09 (no unpriced lines) |
| l | Documented operational support/maintenance, **48-hour resolution commitment**, fault-reporting procedures, technician/site-visit details | none — manual |

## 3. Evaluation method (pack "Information to bidders", quoted)

Two stages, **no scored functionality and no numeric threshold**:

- "**1st stage: Administrative compliance and mandatory requirements** —
  Bids received will be evaluated based on administrative compliance
  (Supply chain Management requirements) and other mandatory requirements
  to assess bidder's ability to execute the contract" — i.e. §1 and §2
  above are pass/fail eliminations.
- "**2nd Stage: Price and specific goals** … on the 80/20 preference point
  system, where 80 points is for Price and 20 points is for specific
  goals", split: "Points for HDI status (51% Black owned) **10** · Points
  for 51% Women's Equity **4** · Points for black person with Disability
  **3** · Points for 51% owned Youth firm **3** · Form not completed or
  submitted 0." Proof: "a CSD number or CIPC documents indicating share
  ownership … or a comprehensive CSD report" naming owners, gender, race,
  age, disability (medical certificate verifies disability).

The SDK's per-tender `functionality_threshold` is simply **not applicable**
here — a useful negative case: the corpus threshold distribution (n=238,
mode 70) describes packs that score functionality; this pack eliminates on
mandatory requirements instead.

## 4. Critical criteria and kill rules (pack page 14 + brochure, quoted → SDK rules)

| Pack text (quoted) | SDK rule |
|--------------------|----------|
| "BIDS/PROPOSALS RECEIVED AFTER THE CLOSING DATE AND TIME BE LATE AND CANNOT BE ADMITTED FOR CONSIDERATION"; box open 07:30–16:00 weekdays, Reception Office Room 53 (cnr Irwin and Scholtz) | KILL-01 (KILL-LATE) — **fired in this retrospective sample** |
| "ONLY BIDDERS WHO ARE REGISTERED ON THE CENTRAL SUPPLIER DATABASE WILL BE CONSIDERED" | GATE-CSD |
| "ALL PAGES OF THE BID DOCUMENT MUST BE INITIALED AND SIGNED WHERE REQUIRED"; "INITIAL EVERY PAGE … AT THE BOTTOM" | KILL-02 / KILL-10 |
| "BID DOCUMENT MUST BE COMPLETED IN INK"; brochure §3.2 "signed in **black ink**. Failure to sign ALL relevant documents will invalidate the bid" | KILL-07, KILL-10 |
| Sealed envelope with service description + bid number, deposited in the tender box | KILL-16 (KILL-CHANNEL); brochure §3.4 "Tenders submitted by facsimile, telex, telegram or e-mail WILL NOT BE CONSIDERED" |
| "ALL PRESCRIBED SUPPORTING DOCUMENTS … MUST BE ATTACHED" | KILL-02 (KILL-RETURNABLE) |
| "NO BIDS WILL BE CONSIDERED FROM PERSONS IN THE SERVICE OF THE STATE" (+ MBD 4 questionnaire with MSCM Regulations definition) | GATE-STATE-EMP / KILL-04 |
| Form A Form of Bid: "Failure to complete this document will result in the whole bid document being rejected"; Form B: "Failure to complete all blank spaces … will render the bid liable to rejection" | KILL-02 / KILL-10 |
| Brochure §3.3: "A definite price must be indicated … 'price to be negotiated' or 'to be advised' are not acceptable" | KILL-09 (KILL-PRICE-BLANKS) |
| Brochure §3.6: "The complete Bid Documents … must be submitted in the same order and no part thereof must be removed"; contents page: "DO NOT REMOVE ANY PAGES" | KILL-13 (KILL-RETYPED) / the Overberg "do not dismember" pattern |
| MBD 8: rejection for defaulters register / fraud convictions / terminated state contracts; MBD 9 collusion certificate | GATE-DEFAULTERS, KILL-06 |
| Bid validity: brochure §3.5 "normally 90 days"; GCC §19: "If no period is mentioned, the bid shall remain open … for a period of 90 days" | FORM-VALIDITY |

## 5. Forms actually issued in the pack (pages 40–65) vs the SDK's MBD fixture set

The pack's own contents page: Invitation to Bid (1–14), Information
Brochure (15–21), General Conditions of Contract (22–33), Preference point
explanation (34–39), "Forms to be completed by the Bidder" (40–65):

| Pack form | Nearest SDK template | Match |
|-----------|---------------------|-------|
| Form A — Form of Bid (black ink, bidder + **two witnesses**) | MBD1 (cover/offer) | partial — buyer-authored, not MBD1 |
| Form B — Signatory Authorisation (+ certified authorisation copy) | none | manual |
| Form C — Declaration of Interest (**legacy HDI equity claim**, "…% = … Points out of 20 (<R1 000 000)", subcontracting ≤25%) | MBD4/MBD6.1 hybrid | none — legacy municipal form |
| MBD 4 — Declaration of Interest (labelled "ANNEXURE C") | MBD4 | **exact** |
| MBD 6.1 — Preference Points Claim, PPR **2022**, 80/20, specific-goals table | MBD6.1 | **exact** |
| MBD 8 — Past SCM Practices | MBD8 | **exact** |
| MBD 9 — Certificate of Independent Bid Determination | MBD9 | **exact** |
| Form D — Certificate of Preference for **Local Content and SABS mark** (Section 35, Local Government Ordinance **1939**) | MBD6.2 (nearest) | none — 1939-Ordinance form, not the SBD/MBD 6.2 local-content instrument |
| Form E — OHS Act s37(2) contract (Act 85 of 1993) | none | manual (SDK has no OHS agreement template) |

**Notable pack self-contradiction (recorded as corpus evidence):** the pack
simultaneously carries the **pre-2011 HDI equity-ownership preference
framework** (Information Brochure 2.1.5 and the whole Preference Point
Explanation, PPPFA 2000 regulations; Form C claims "20 points … <R1 000
000") **and** the **PPR 2022 specific-goals MBD 6.1** (HDI 10 / women 4 /
disability 3 / youth 3). The operative scoring is the MBD 6.1 table (it
matches the "Information to bidders" page), but a bidder must complete
both. No SDK structure can represent a pack whose preference frameworks
disagree — see findings F-12.

## 6. SDK-generated compliance checklist (rule matching run for this bid)

Running SDK `rules.rule_applies` with `{regime: MBD, estimated_value:
2573750, institution: "Musina Local Municipality"}` attached **36 rules**:
the universal Fatal spine (GATE-CIPC, GATE-CSD, GATE-DEFAULTERS,
GATE-STATE-EMP, GATE-TCS, KILL-01 – KILL-18, KILL-20, KILL-22 – KILL-25),
the MBD-conditional **GATE-RATES and KILL-19** (both fired from the regime
alone — GATE-RATES matches page 2's directors-and-company rates demand
almost word-for-word), Curable FORM-VALIDITY / GATE-SUBCONTRACT /
PRICE-SECURITY / PRICE-VAT, and Points-only GATE-BBBEE / SCORE-PREF-CLAIM.
GATE-MBD5 correctly stayed off below R10m — but see §1: this pack demands
AFS anyway, decoupled from value.

**Notable non-fire, again:** GATE-POPIA did not attach — its trigger is a
buyer-pattern list (SANRAL/Transnet). This time the miss is starker than on
the TWK website sample: **POPIA compliance is explicit specification text
here** — §4(c) requires "compliance with POPIA, PAIA, and related
legislations", the abbreviations table defines both acts, spec (kk)
requires the system "Must be hosted in South Africa, by South Africans",
and spec (pp) requires 18-month retention of call recordings — citizen
personal information end to end. The optional POPIA form generates in the
MBD pack, but no checklist row demands or tracks any of it. Everything in
§2 above (the twelve mandatory-requirement returnables) is likewise
untracked by fixtures and carried as manual rows.
