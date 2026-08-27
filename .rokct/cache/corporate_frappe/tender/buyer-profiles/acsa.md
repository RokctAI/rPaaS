# Buyer Quirk Sheet: Airports Company South Africa SOC Ltd (ACSA)

**Buyer:** Airports Company South Africa SOC Ltd (ACSA)
**Kind:** State-Owned Enterprise (SOE) — national airports operator (majority state-owned, JSE-adjacent governance; uses NEC3 contract suite and CIDB Standard Conditions of Tender rather than plain MBD/municipal SCM rules)
**Packs sampled:** 10 packs (1 unusable — spreadsheet-extraction artifact with no readable text)
- `acsa-kingphalo-roads-rehab` (analysis JSON) — signed NEC3 PSC, King Phalo Airport roads/taxiway rehab professional services, SCM ref 12125
- `acsa-power-retic-maint-rfq` (analysis JSON) — RFQ74541, Cape Town Intl Airport power reticulation (MV/LV) maintenance
- `ocds-9t57fa-165118` — bid document, O.R. Tambo Intl Airport, RFQ 74561 (roofing/other works, PSP-type)
- `ocds-9t57fa-164199` — bid document, replacement of perimeter fence, O.R. Tambo Intl Airport
- `ocds-9t57fa-165887` — bid document, Enablement Works for New Re-Aligned Runway Project, CTIA8322/2026/RFP, Cape Town Intl Airport
- `ocds-9t57fa-165400` — bid document (airport(s) not fully captured in sampled text), 28 Aug 2026 closing
- `ocds-9t57fa-165696` — signed NEC3 contract, manufacture/supply/install fuel infrastructure, O.R. Tambo Intl Airport
- `ocds-9t57fa-165202` — signed NEC3 TSC, Provision of Comprehensive Pest Control Services, O.R. Tambo Intl Airport (ORTIA8189/2026/RFP)
- `ocds-9t57fa-165644` — signed NEC3 PSC, Upgrade of Water System Pipes (36 months), O.R. Tambo Intl Airport, project 6338
- `ocds-9t57fa-165347` — unreadable (raw Excel/formula-reference dump, no prose); **excluded from all findings below**

Date of profile: 2026-08

---

## 1. Submission channel & rules

ACSA runs on the CIDB Standard for Uniformity in Construction Procurement (Annex C, Government Notice 423 of 2019) as its baseline "Standard Conditions of Tender," then **overrides it per-tender** with a specific Tender Notice instruction — and the two frequently conflict inside the same document.

- **Two channel patterns exist across the sample, tender-by-tender — always check the specific notice, never assume:**
  - **Email-only** (seen in `ocds-9t57fa-165118`, `acsa-power-retic-maint-rfq`, `ocds-9t57fa-165400`): submit to a single named ACSA mailbox (e.g. `acsarfq@airports.co.za`), split into **at least 4 attachments of ≤4MB each** (no single large attachment), explicit "do not Cc or Bcc any Acsa employee," and a hard rule that "Bid submission sent to any other email apart from the above email will NOT be considered." Quote (`ocds-9t57fa-165118`): *"Bidders must not email their submission as one big attachment. Kindly break your submission in at least (04) four or more attachments of 4mb each."*
  - **Dual-channel, physical-governs** (`ocds-9t57fa-165887`, `ocds-9t57fa-164199`): a physical Tender Box at a named airport office (e.g. "Tender Box B, ACSA North Wings Offices, International Terminal Building 3rd Floor, O. R. Tambo International Airport") **plus** an emailed electronic copy of the same bid — and ACSA is explicit that using only one channel is wrong: *"PLEASE NOTE THAT BOTH METHODS MUST BE UTILIZED. BIDDERS SHOULD NOT CHOOSE JUST ONE OF THEM AND THE PHYSICAL SUBMISSION INFORMATION WILL TAKE PRECEDENCE SHOULD THERE BE A DISCREPENCY BETWEEN THE TWO SUBMISSION METHODS. FAILURE TO SUBMIT THE PHYSICAL DOCUMENTS BEFORE THE CLOSING TIME WILL RESULT IN A DISQUALIFICATION."* (`ocds-9t57fa-165887`)
- **Sealing/labeling (physical-channel tenders):** 1 Original + 1 Copy, in clearly marked sealed envelopes labelled "Original"/"Copy," each bearing tenderer name/contact, tender reference number, and description; plus a **Bid Register** must be signed on delivery. Quote (`ocds-9t57fa-164199`): *"The bidder must submit bids in Printed (1 Original and 1 Copy). Bids must be sealed in clearly marked envelopes/package indicating which is 'Original' and which is 'Copy'... The Bid Register must be completed when submitting/depositing the tender document."*
- **Late bids are a hard bar regardless of channel:** *"Bids which are submitted after the closing date and time will not be accepted... Airports Company South Africa SOC Limited will not be liable for any late bids."* — and proof of *posting/sending* is explicitly not accepted as proof of delivery (`acsa-power-retic-maint-rfq`).
- Fax/telex/telegraph/unsanctioned email are always rejected as a submission channel: *"Telephonic, telegraphic, telex, facsimile, e-mailed tenders will not be accepted."* (`ocds-9t57fa-164199`, `ocds-9t57fa-165887`, `ocds-9t57fa-165118`).
- Some tenders require every page of the bid document be signed/stamped as proof of having read it, in addition to the formal signature page. Quote (`ocds-9t57fa-165400`): *"The bottom of each page of the bid documents must be signed or stamped with the bidder's stamp as proof that the bidder has read the tender documents."*
- Compulsory-briefing attendance gates addenda distribution and eligibility to submit at all (see Section 7).

## 2. Municipal-arrears / rates clause

**Not observed in sampled packs.** ACSA is a national SOE, not a municipality, and none of the 9 readable packs contain a "not more than X days in arrears with rates/municipal accounts" clause of the kind seen in municipal SCM policies. Grep across all 9 readable files for "arrears," "rates and taxes," and "municipal" returned no ACSA-specific clause (one incidental, unrelated hit for "provincial/municipal/district" as an entity-location checkbox in `ocds-9t57fa-165400`, not an arrears test).

## 3. B-BBEE treatment

**Preference points only — never a hard pre-qualification gate.** ACSA consistently uses the 80/20 Preferential Procurement Regulations 2022 formula (bids up to ~R50m; 90/10 above that per the general SBD 6.1 boilerplate, per `acsa-power-retic-maint-rfq`) and is explicit, repeatedly, across independent tenders, that failing to prove B-BBEE status costs points but never disqualifies:

- Quote (`ocds-9t57fa-165118`): *"...submit proof, the bidder will score zero (0) out of 20 or out of 10. ACSA will not disqualify the bidder."*
- Quote (`ocds-9t57fa-164199`): *"...to submit proof, the bidder will score zero (0) out of 20. ACSA will not disqualify the bidder."*
- Quote (`ocds-9t57fa-165400`): same wording, "ACSA will not disqualify the bidder."
- Quote (`acsa-power-retic-maint-rfq`): *"If a bidder fails to meet the Specific goals... and to submit proof, the bidder will score zero (0) out of 20. ACSA will not disqualify the bidder."*

Standard points table appears identically across packs: B-BBEE Level 1 = 5 pts, Level 2 = 4.5, Level 3 = 4, Level 4 = 3, Level 5 = 2, Level 6 = 0.5, Level 7 = 0.3, Level 8 = 0.1, non-compliant = 0; plus specific-goal points (5 pts each) for Black-youth-majority-owned, Black-women-majority-owned, and disability-majority-owned entities (`acsa-power-retic-maint-rfq`).

Evidence accepted: sworn B-BBEE affidavit **or** SANAS-accredited certificate; JVs need a consolidated SANAS-accredited certificate (`acsa-power-retic-maint-rfq`).

Downstream contract requirement (not a bid gate): where sub-consultants are engaged via the 3-quote system post-award, their B-BBEE level and spend must be tracked and reported to ACSA for the life of the contract (`acsa-kingphalo-roads-rehab`).

Only exception found to "never disqualifies": fraud. If B-BBEE points were *"claimed or obtained on a fraudulent basis"* the bid/contract can be terminated (`acsa-power-retic-maint-rfq`) — the risk is fraud, not honest non-submission.

## 4. Cure/condonation policy

ACSA draws a sharp, well-defined line between **curable arithmetic/clarification issues** and **fatal responsiveness defects** — it does not have a broad discretionary condonation clause.

- **Curable (narrow):** clarification of a submitted tender offer is allowed post-submission, but strictly limited to "correction of arithmetical errors by the adjustment of certain rates or item prices... No change in the competitive position of tenderers or substance of the tender offer is sought, offered, or permitted." (`ocds-9t57fa-165118`, C.2.17). Pricing-schedule error rules from `acsa-power-retic-maint-rfq`: amount in **words governs** over figures; where rate × quantity is wrong, the **line item total governs** and the rate is corrected (except gross decimal-point misplacement, where the line item total as quoted still governs). This arithmetic check is only performed on the **highest-ranked** tender post-evaluation, not all bids.
- **Fatal, not curable:** *"Reject a non-responsive tender offer, and not allow it to be subsequently made responsive by correction or withdrawal of the non-conforming deviation or reservation."* (`acsa-power-retic-maint-rfq`). Incomplete data "not provided... completely and, in the form, required" may itself be treated as non-responsive.
- **Alterations must be initialled at submission time** (not curable after the fact by explanation): *"Do not make any alterations or additions to the tender documents, except to comply with instructions issued by the employer... All signatories to the tender offer shall initial all such alterations."* (`acsa-power-retic-maint-rfq`)
- **Alternative bids are never accepted** as a workaround for a non-compliant main bid: *"Alternative bids will not be considered."*
- No condonation/waiver-of-defect clause discussing ACSA's discretion to overlook a missing return was found in the sampled functional-conditions text; the only "waiver" language found was generic no-waiver-of-rights boilerplate inside the signed NEC3 contracts (`ocds-9t57fa-165118`, `ocds-9t57fa-164199`, `ocds-9t57fa-165887`, `ocds-9t57fa-165400`), which is a contract-interpretation clause, not a bid-defect cure mechanism. Treat as "not observed" beyond the arithmetic-only clarification window above.

## 5. Security/vetting requirements

- **Post-award security vetting is conditional, not universal**, appearing as a discretionary evaluation-stage step: *"Security Vetting — If deemed necessary"* listed in the process flow of Stage 3/4 evaluation (`ocds-9t57fa-165887`).
- **Airside/landside access vetting is the dominant, near-universal control** on airport-site contracts rather than personnel security vetting per se: airside personnel/vehicle permits require completed airside induction training, ID document (driver's licence explicitly NOT accepted at some sites), safety boots, and reflector vest; cell phone use on airside is restricted to permit-holders. Quote (`ocds-9t57fa-165202`): *"Proof of having attended the airside induction training course is required for all personal permit applications."* / *"No works are to take place if a security breach has not been secured, applies to Airside."*
- **PEP/DPIP disclosure** is a mandatory bid returnable: Form A12, Declaration of Interest and Politically Exposed Person/Domestic Prominent Influential Person disclosure for directors/shareholders/management (`acsa-power-retic-maint-rfq`).
- **Tender Defaulters Register / Restricted Suppliers List check** is automatic and non-discretionary: *"Where a person/s are listed in the Register for Tender Defaulters and / or the List of Restricted Suppliers, that person will automatically be disqualified from the bid process."* (`acsa-power-retic-maint-rfq`, `ocds-9t57fa-165887`)
- **POPIA (data protection) obligations flow into the signed contract**, not the bid stage: a dedicated POPIA Annexure appears in NEC3 professional-services contracts, obliging the Operator (consultant) to act only on ACSA's documented instructions, notify ACSA of any breach, use sub-operators only with prior written authorisation, delete/return personal information at contract end, and submit to audits — modelled directly on POPIA ss.20-21. Quote (`ocds-9t57fa-165644`): *"the Service Provider shall notify the Company immediately where there are reasonable grounds to believe that the personal information of a data subject has been accessed or acquired by any unauthorised person."*
- **Confidentiality & Non-Disclosure Agreement (Form A11)** is a mandatory bid returnable with a **2% of annual turnover penalty clause** for misuse of ACSA's brand/IP (`acsa-power-retic-maint-rfq`).
- No integrity-pact/anti-bribery pledge distinct from the standard SBD4 anti-collusion declaration and corrupt-practices disqualification clause was found (see Section 4/8).

## 6. Financial demands

- **Bidder-side insurance is mostly a post-award condition, not a bid-stage document**, but its exact levels are locked in the signed contract:
  - Professional Indemnity: **R5 million**, held for 24 months post-completion (professional-services contracts) (`acsa-kingphalo-roads-rehab`)
  - Public Liability (consultant, professional-services contracts): **R10 million** (`acsa-kingphalo-roads-rehab`)
  - Contract will simply **not be signed** without valid insurance and a valid COIDA Letter of Good Standing — both are explicit conditions precedent to contract execution, not bid disqualifiers: *"NB: The contract will not be signed without a valid insurance."* / *"NB: The Contract will not be signed without a valid letter of good standing with the workers Compensation commissioner (COIDA)."* (`acsa-power-retic-maint-rfq`)
- **Distinctive: on airside construction contracts, ACSA itself buys and pays for the bulk of the insurance program** via "Principal Controlled Insurance" (PCI) rather than requiring the contractor to hold it — for contracts up to R150 million / 36-month construction period / 24-month defects liability. ACSA-arranged cover includes: Contract Works (full value of Works), Contractors Public Liability at **R100,000,000** per occurrence, Removal of Lateral Support Liability at **R50,000,000**, Contract Works SASRIA at **R500,000,000** aggregate, Aviation Liability at **R2,000,000,000** per occurrence, and Design & Construct Professional Indemnity at **R25,000,000** (a shared annual aggregate across *all* ACSA contracts, so it can be exhausted by other projects' claims). The contractor bears policy deductibles (R150,000 rising to R250,000 for testing/commissioning on Contract Works; R75,000 each on Public Liability and Lateral Support claims) and must price any supplementary cover itself. Quote (`ocds-9t57fa-165696`): *"the Employer shall effect and maintain for the duration of the construction and maintenance periods of the Contract... Public Liability Insurance... with a limit of indemnity of R100,000,000... Aviation Liability Insurance... with a limit of indemnity of R2,000,000,000."*
- **Performance bond:** typically **20% of the total of the Prices**, unconditional/on-demand, provided by a bank or insurer acceptable to ACSA, valid until end of contract period with a duty to extend it 4 weeks before expiry or ACSA claims the full amount as cash security (`ocds-9t57fa-165696`, `ocds-9t57fa-165644`).
- **Retention:** 5% of the total of the Prices (`ocds-9t57fa-165696`).
- **Bank Letter is a "Letter of Good Standing," not a bank confirmation/rating letter per se** — though a rating is invited: *"B4: Bank Letter: Letter of Good Standing from Bidder's Bank preferably with bank rating for tender sum."* (`ocds-9t57fa-165118`, `ocds-9t57fa-164199`, `ocds-9t57fa-165400`) — this is listed as a document required "only for tender evaluation purposes" (category B), separate from the mandatory Stage-2 administrative returnables (category A).
- **Letter of Solvency** required from bidder's auditors/accountants (`ocds-9t57fa-165118`), functioning in place of a full audited-financial-statements demand — no explicit "submit N years of audited financial statements" requirement was found in the sampled packs; treat that specific ask as **not observed**.
- **Delay damages / liquidated damages:** 2% of contract value per week per section, capped at 10% of total contract value on the professional-services contract (`acsa-kingphalo-roads-rehab`); on the fuel-infrastructure works contract, capped at 20% of total Prices with a stated daily rate (`ocds-9t57fa-165696`).
- **Pricing is fixed with no escalation clause** as standard: *"This contract shall not be subject to Contract Price Adjustments, foreign fluctuations, etc and all rates and prices shall remain FIXED, final and binding for the full duration of this contract."* (`acsa-power-retic-maint-rfq`) — the only relief is a CPI-based price review right if ACSA's own evaluation drags on past the 12-week (84-day) bid validity period.

## 7. Functionality norms

ACSA uses a classic threshold-gate functionality score (0-100) that must be cleared before Price/Preference (80/20 or 90/10) is even considered — but **the threshold varies materially by tender complexity**, so it is not a fixed constant:

- 60/100 — `ocds-9t57fa-164199` (perimeter fence replacement)
- 70/100 — `acsa-power-retic-maint-rfq` (MV/LV power reticulation maintenance) and `ocds-9t57fa-165400`
- 75/100 — `ocds-9t57fa-165118`

Criteria style is heavily **evidence-format-strict**: reference letters/completion certificates on client letterhead with contactable details are typically the *only* acceptable proof of experience, and purchase orders/appointment letters/award letters/invoices are explicitly excluded. Quote (`acsa-power-retic-maint-rfq`): *"Purchase orders, appointment letters, award letters and invoices explicitly NOT accepted as proof."* Similarly (`ocds-9t57fa-165887`): *"Completion certificates, appointment letters and reference letters will not be accepted"* for that tender's Form D1/D2 project-reference route (note: the *acceptable* proof format is itself tender-specific — verify per pack rather than assuming one universal rule). ACSA independently verifies references and professional registrations rather than taking them on trust (`ocds-9t57fa-165887`: *"ACSA will verify project references"*; key persons must be registered with Councils recognised by the CBE and *"ACSA will verify all registrations"*).

Scoring bands frequently have **hard cliffs** rather than smooth gradients — e.g. 5+ reference letters = full 40/40 on the Company Experience line, 3-4 = 30, fewer than 3 = 0 (`acsa-power-retic-maint-rfq`) — making the difference between winning and being eliminated pre-price a matter of one extra document.

## 8. Distinctive kill rules / quirks

- **Dual-channel bids where the physical copy silently overrides the electronic one, with an explicit warning against choosing only one method** — this is a genuine trap: skipping the physical Tender Box submission is fatal even if the email arrived on time and complete (`ocds-9t57fa-165887`).
- **CIDB contractor grading is a hard eligibility gate that varies wildly by project** — sampled thresholds range from 2EP up to 7CE across different tenders (`ocds-9t57fa-165400`: 2EP; `acsa-power-retic-maint-rfq`: 3EP; `ocds-9t57fa-165118`: 3EB; `ocds-9t57fa-165887`: 7CE) — bidders must check the specific Tender Data grading, not assume a standard level.
- **Internal document contradictions are routine and intentional-by-override**: the generic CIDB Annex C boilerplate (sealed original+copy+USB flash drive, in-person delivery) is carried through nearly every pack verbatim even when the project-specific Tender Notice supersedes it with email-only or dual-channel rules — ACSA's own packs tell bidders point-blank to follow the specific instruction over the generic one (`ocds-9t57fa-165887`, `acsa-power-retic-maint-rfq`).
- **Sub-consultant/subcontractor spend triggers an ongoing compliance obligation**, not just a one-time check: any sub-consultant/specialist engaged post-award must go through a 3-quote process, submit BBBEE certificate + tax clearance, and have that tracked/reported to ACSA for the life of the contract — failure blocks payment approval, not just disqualifies the sub (`acsa-kingphalo-roads-rehab`).
- **ACSA self-insures the big-ticket airside construction risks (up to R2bn Aviation Liability) rather than requiring the contractor to carry them**, a structure distinct from the typical SOE/municipal pattern of pushing all insurance onto the bidder — see Section 6.
- **Live-airport operational constraints materially shape scope and schedule risk**: airside/landside access-permit vetting, restricted night-work hours near terminals, strict on-site speed limits (40-50 km/h), no unattended bags near security, and delivery-vehicle routing via specific yards only — these are described in winning-insights as a common source of underpriced/underscheduled losing proposals (`acsa-kingphalo-roads-rehab`).
- **Environmental non-compliance penalties are a named, separate SOE-specific instrument** (EMS 048 permit) with a discretionary R200-R20,000 penalty band levied at ACSA's discretion (`acsa-kingphalo-roads-rehab`) — not observed in the other sampled packs, so may be project-specific rather than universal.
- **Tender opening register is published to the National Treasury eTenders website** even though ACSA is a corporatised SOE running its own CIDB-based process: *"Tender opening register will be uploaded on National Treasury e-tenders website."* (`ocds-9t57fa-165118`) — a transparency mechanism worth noting for bidders assuming SOE processes are opaque.
- **Design consultants can be tasked with building the evaluation tool for the next-stage tender**: the Kingphalo professional-services scope required the consultant to produce the "Tender Scorecard Matrix" used to evaluate the downstream construction tender — an unusual scope item that gives the professional-services winner influence over how the follow-on contract will be scored (`acsa-kingphalo-roads-rehab`).
