# Buyer Quirk Sheet — South African National Roads Agency SOC Limited (SANRAL)

**Buyer:** South African National Roads Agency SOC Limited (SANRAL)
**Kind:** State-Owned Entity (SOE) — national roads authority, JSE debt-listed
**Packs sampled:** 10 documents (7 usable/non-empty), covering a Consulting Engineering Services JV appointment, a Security Services RFT (two near-identical regional variants), three Routine Road Maintenance consulting-engineering tender notices, a commercial property valuation panel notice, and two civil-works (CIDB-graded) tender notices.
- `sanral-consulting-eng` (analysis json; Bid C.002-056-2024/1, Kloppersbos/Pyramid Road CD project)
- `ocds-9t57fa-164220` (RFT HO/1037/68125/2026/04, Security Services — Gauteng Provincial Office)
- `ocds-9t57fa-164236` (RFT HO/1037/68125/2026/04, Security Services — near-duplicate/second copy)
- `ocds-9t57fa-165706` (NRA2026/0238, Consulting Eng. RRM — Johannesburg Freeway)
- `ocds-9t57fa-165709` (NRA2026/0238, Consulting Eng. RRM — Ekurhuleni Freeway)
- `ocds-9t57fa-165705` (2026/0240, Consulting Eng. RRM — Tshwane Freeway)
- `ocds-9t57fa-164841` (Commercial Property Valuation Services panel, 3-year)
- `ocds-9t57fa-165702` (N11 Section 10 Special Maintenance, Limpopo — CIDB 9CE)
- `ocds-9t57fa-165698` (R71/D4020 Grade Separated Interchange, Limpopo — CIDB 9CE)
- `ocds-9t57fa-164446` — empty file, no content extracted; excluded from analysis.

Date: 2026-08

---

## Submission channel & rules

SANRAL runs a **strict physical tender-box regime** across every pack sampled — no electronic or e-mail submission channel is offered for any of these bids, and the notices repeat the same prohibition almost verbatim:

> "Telegraphic, telephonic, telex, facsimile, e-mailed tenders will NOT be accepted." (`ocds-9t57fa-165706`, `165709`, `165705`, `165702`, `165698`)

Tenders go into a physical tender box at the relevant regional office (Gauteng Provincial Office, 38 Ida Street, Menlo Park, Pretoria for most Gauteng-region packs; Centurion Central Operations Centre for the valuation panel), by a hard closing date/time — no grace period. Late tenders are categorically refused: "No late tenders will be accepted after closing date and time" (repeated in all five notice-style packs above).

The Security Services RFT pack gives the most granular sealing/copy-count instructions seen in the sample:

> "The RFT submissions will close at 12H00 on Friday, 04 September 2026 and all RFT documentation must be sealed in a clearly marked envelope and placed in the tender box... Bidders must submit one original plus one hard copy and electronic copy (memory stick)... The RFT envelope must also contain the Bidder's details on the back of the envelope." (`ocds-9t57fa-164220`, `164236`)

So the pattern is: sealed envelope, box delivery, hard-copy original + hard copy + a memory-stick electronic copy bundled inside one sealed package (not a separate electronic portal upload). Bidder name/contact must appear on the cover page of the bid document itself as well as the envelope. The consulting-engineering main-tender pack (`sanral-consulting-eng`) references the same "Requirements for sealing, addressing, delivery, opening and assessment of tenders are stated in the Tender Data" boilerplate but the Book 1/Tender Data volume itself (where the numeric details would sit) was not in that extract — "Not observed in sampled packs" for that document's own sealing specifics beyond the pointer.

Compulsory clarification/briefing sessions are now run virtually via Microsoft Teams (a shift from the traditional in-person site briefing model seen at some other SOEs), with strict late-arrival exclusion: "Late arrivals (15 Minutes late) will not be allowed to participate in the meeting... their submissions shall be declared non-responsive" (`165702`, `165698`), and for the Consulting Eng RRM notices, a slightly softer but still hard registration cut-off: "Late registration will not be allowed, and their submissions shall be declared non-responsive" (`165706`, `165709`, `165705`). One representative may not represent more than one tenderer at the briefing, enforced in every notice sampled.

## Municipal-arrears / rates clause

**Not observed in sampled packs.** None of the ten documents contain a municipal rates/property-tax arrears clause (e.g., a "not more than 90 days in arrears" test). SANRAL's analogue integrity-debt check is instead a **debt-to-SANRAL-itself** declaration, not a municipal one:

> "FORM A4: DECLARATION OF BIDDER'S CURRENT STATUS OF ANY DEBT OUTSTANDING TO [SANRAL]... the Bidder or any of its Directors/Members do not have any debt outstanding to SANRAL, other [than disclosed]" (`ocds-9t57fa-164220`, `164236`)

This is a self-declared debt-to-buyer check rather than a local-authority rates/utilities arrears window; nothing tying eligibility to municipal accounts was found in any pack.

## B-BBEE treatment

**Preference points only — not a hard pre-qualification gate**, consistent across both the consulting-engineering pack and the Security Services RFT:

> "The tenderer will score 0 (zero) points if: The B-BBEE certificate is not submitted or submitted B-BBEE certificate that has expired or is not valid..." (`sanral-consulting-eng`) — i.e., a defective certificate forfeits *all* preference points but does not by itself disqualify an otherwise-responsive tender.

Standard PPPFA/2022-Regulations mechanics apply: 80/20 system for tender value up to R50m (incl. taxes), 90/10 above R50m, the applicable system determined only after tenders open based on the lowest acceptable price (`sanral-consulting-eng`). Points table runs Level 1 = 10.00 (90/10) / 20.00 (80/20) down to Level 8 = 1.00/2.00; non-compliant = 0.

Certificate mechanics are detailed and strict on form (SANAS-accredited verification agency, valid at closing date, issued <12 months prior, sworn affidavit route for EME/QSE requiring an accompanying audited financial statement or management account, project-specific consolidated certificate for unincorporated JVs bearing the SANRAL contract/project name and number):

> "Have a date of issue less than 12 (twelve) months prior to the tender closing date... In an event of an un-incorporated Joint Venture (JV), a valid project specific (must contain SANRAL project name and number) consolidated B-BBEE Verification Certificate in the name of the JV shall be submitted." (`ocds-9t57fa-164220`)

Only the B-BBEE contributor-status-level goal is scored in the sampled preference tables (no separate local-content/youth/disability/women-ownership scoring line observed), though such shareholding data must still appear on the certificate itself (`sanral-consulting-eng`). Separately, the consulting-engineering pack layers on a **Targeted Enterprise sub-contracting requirement** (EME/QSE, ≥51% black-owned, Level 1–2, no shared equity with the prime, CSD-registered) that becomes a binding contractual percentage commitment upon award — this is a contract-execution obligation distinct from the scored preference-points mechanism.

## Cure/condonation policy

SANRAL shows a mixed but generally **narrow cure regime** — most defects are treated as fatal (non-responsive) rather than curable, with a small number of specific, time-boxed exceptions:

- **No cure for missing/incomplete Pricing Schedule or alternative-offer defects** — these are immediate non-responsive causes, not curable: "The tenderer will be declared non-responsive if: A signed Form of Offer is submitted with an incomplete Pricing Schedule" (`sanral-consulting-eng`).
- **A narrow, specific cure window does exist for unbalanced/out-of-proportion rates**: "if the tenderer fails, within a period of seven (7) days of having been notified in writing by the Employer to adjust the unit rates or lump sums for such items" — i.e., SANRAL gives 7 days to fix flagged pricing anomalies before declaring non-responsiveness, but only for this specific defect class (`sanral-consulting-eng`).
- **Post-award compliance cure windows are more generous but strictly enforced**: SARS tax compliance has a 7-working-day cure window post-acceptance before the agreement is deemed repudiated; banking/vendor registration has a 14-calendar-day window; insurance has a 14-day window but **carries no cure at all if missed** — it converts straight into an automatic minimum 12-month tender ban (see Security/vetting section below) (`sanral-consulting-eng`).
- The Security Services RFT pack shows **no condonation/clerical-error language at all** — searches for "condon", "clerical error", "minor deviation", "rectify" returned nothing; disqualification triggers there (false disclosure, non-disclosure of CSD-linked companies, collusion, conflict of interest) read as final, not curable: "Failure to disclose all CSD-registered active companies linked to all Directors will lead to disqualification" (`ocds-9t57fa-164220`).

Net pattern: SANRAL curing is exceptional and enumerated (rate anomalies, SARS status, banking registration, each with its own named window) rather than a general "opportunity to correct minor defects" clause.

## Security/vetting requirements

This is one of SANRAL's most distinctive features relative to typical SA public-sector buyers: **State Security Agency screening as a condition of contract award**, at least for security-services procurement:

> "Acceptance of this bid is subject to the condition that the Successful Bidder will be subjected to security screening conducted by the State Security Agency and appointment can only be finalised upon the Bidder obtaining a positive security screening outcome." (`ocds-9t57fa-164220`, `164236`)

Layered on top of that, the same pack requires the bidder's own personnel-vetting regime as a scope-of-work obligation, including **annual polygraph testing** for the life of the contract:

> "The successful security service provider shall conduct pre-employment security screening for all security officers to be deployed at SANRAL, this includes criminal record checks, identification verification, polygraph tests and any other applicable screening... Periodic security screening shall take place for the duration of the contract with annual polygraph testing" (`ocds-9t57fa-164220`)

POPIA is handled via a dedicated returnable form (Form A13/FORM 13: Protection of Personal Information) requiring the bidder to acknowledge SANRAL's data-processing rights and confirm awareness of Section 5 POPIA rights — a standing returnable schedule rather than a bespoke consent clause (`ocds-9t57fa-164220`, `164236`). Separately, both the security-RFT and consulting-engineering packs use integrity-style declarations: Register for Tender Defaulters / Database of Restricted Suppliers checks with automatic disqualification (`ocds-9t57fa-164220`), a Fronting Practices certificate with DTI-reporting language, a Bidder's Disclosure form on organ-of-state employment/relationships, and (in the consulting-eng pack) a specific-goals fraud clause allowing disqualification if B-BBEE preference points were "claimed or obtained on a fraudulent basis" (`sanral-consulting-eng`). No formal "integrity pact" document by that name was observed in any pack — the function is distributed across several named declaration forms (A5–A15 series) instead.

## Financial demands

- **Professional Indemnity, General Public Liability and Third Party Liability insurance, each at R7.2 million cover**, due within 14 calendar days of the Form of Acceptance with ongoing monthly proof of validity thereafter — and uniquely, missing this specific deliverable (unlike almost any other post-award item in the pack) triggers an **automatic minimum 12-month debarment from all future SANRAL tenders**:

  > "In addition to any other rights of remedy the Service Provider shall, if (i) above has not been met, be automatically barred from tendering on any of our future tenders for a period determined by us but not less than 12 (twelve) months, from the date of tender closure." (`sanral-consulting-eng`)

- **Performance Guarantee of 5% of the accepted tender sum** (design portion, incl. VAT), due within 14 days of acceptance — for this particular contract the pack notes the *general* Performance Security clause is otherwise waived, i.e., the 5% design-portion guarantee substitutes for it (`sanral-consulting-eng`).
- Audited financial statements are referenced as a due-diligence/verification tool SANRAL reserves the right to demand ("request audited financial statements or other documentation for the purposes of a due diligence exercise" — `ocds-9t57fa-164220`) and are also acceptable supporting evidence behind a B-BBEE sworn affidavit for EMEs, rather than a standing mandatory submission for every bid.
- **No bank-confirmation-letter or credit-rating requirement was observed** in any sampled pack — banking details are handled post-award via the Vendor Application Form/CSD Report plus an indemnity letter confirming bank details match CSD (`sanral-consulting-eng`); this is a registration/verification step, not a solvency test.
- Bid validity: 90 calendar days from closing date in the Security RFT pack (`ocds-9t57fa-164220`, `164236`); the consulting-engineering pack references a validity period stated in the (missing) Tender Data volume without giving the number — "Not observed" for that specific pack.

## Functionality norms

Threshold-and-cutoff, price-blended-after-threshold model, seen clearly in the Security Services RFT:

> "4.2 TEP TWO: Minimum Threshold of 70 points for Technical Criteria... The minimum threshold for technical/functionality [Step TWO] must be met or exceeded for a Bidder's Proposal to progress to Step THREE for final evaluation" (`ocds-9t57fa-164220`, `164236`)

That pack's criteria are experience-banded and reference-letter-driven (years of company experience 0–20 pts, client reference letters 5–20 pts, directors' combined experience 5–20 pts, employed security-staff headcount 5–20 pts, proximity of a Gauteng operational office/control centre 0–20 pts; 100 points total, 70 required to proceed) — a fairly typical SOE three-step (administrative → functionality → price/B-BBEE) evaluation structure. The consulting-engineering pack's own functionality methodology was **not present in the extracted text** (it sits in the missing Book 1/Tender Data volume); the closest analogue found there is a personnel-CV "individual threshold of 85%" applied when evaluating Key Person qualifications against minimum-requirement tables (`sanral-consulting-eng`) — "Not observed in sampled packs" for the numeric functionality weighting/threshold on that specific contract.

## Distinctive kill rules / quirks

- **State Security Agency vetting as a condition precedent to contract finalisation**, plus contractor-run annual polygraph testing of deployed staff for the life of the contract — not something typically seen outside security/facilities-adjacent SOE tenders (`ocds-9t57fa-164220`, `164236`).
- **Insurance non-delivery = automatic ≥12-month debarment from all future SANRAL tenders** — a materially harsher and more specific consequence than the general repudiation language used for every other post-award compliance item in the same pack (`sanral-consulting-eng`).
- **Pricing Schedule governs over the Form of Offer total if the two disagree** — bidders are explicitly told the schedule, not the headline tender-sum figure they wrote on the offer form, is authoritative if there's a mismatch (`sanral-consulting-eng`).
- **Preference-points system (80/20 vs 90/10) is decided only after tender opening**, based on the lowest acceptable price — bidders cannot know in advance which point-scale will price their B-BBEE status, unlike buyers who fix the split upfront in the Tender Data (`sanral-consulting-eng`).
- **Key Personnel capacity cap**: named Key Persons proposed in a bid are capped at a maximum of 6 concurrent SANRAL design-phase contracts, and the Project Leader/Assistant Project Leader/Design Specialists/Contract Engineer generally must be in the *permanent* employment of the tendering entity (freelance/contracted seniors risk non-compliance) (`sanral-consulting-eng`).
- **Conflict-of-interest firewall on downstream tender documentation**: where the consulting engineer itself prepared tender documents for a subsequent Works Contract, SANRAL requires the actual evaluation/Tender Evaluation Report for that Works tender to be performed by a *different* service provider on a comparable SANRAL project — an unusual self-dealing guard embedded directly in the scope of work (`sanral-consulting-eng`).
- **Physical-office-proximity scoring** for security services — points awarded on a sliding scale purely for how close (in km) the bidder's Gauteng operational office/control centre is to the SANRAL site, evidenced by property title, lease, or a utility bill "not older than 3 months" (`ocds-9t57fa-164220`, `164236`) — a locality-based functionality criterion not seen in the other packs sampled.
- **CIDB grading as an absolute gate on civil-works tenders**, with an explicit carve-out barring even correctly-graded emerging enterprises from using a lower "potentially emerging enterprise" designation to qualify: "Tenders from tenderers registered as potentially emerging enterprises with a CIDB contractor grading designation lower than a contractor grading designation required for this tender, will not be accepted." (`ocds-9t57fa-165702`, `165698`) — this sits alongside, not instead of, the B-BBEE preference-points system.
- **JV structuring rule specific to Consulting Eng RRM tenders**: JVs are only permitted if one partner is a Targeted Enterprise, but that JV partner then explicitly does *not* count toward the separate sub-contract Targeted-Enterprise target — the two participation mechanisms are kept deliberately non-fungible: "Joint Ventures (JV) will be allowed on condition that one JV partner is a Targeted Enterprise. The JV partner will, however, not contribute to sub-contract target for Targeted Enterprises." (`ocds-9t57fa-165706`, `165709`, `165705`)
