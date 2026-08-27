# Buyer Quirk Sheet: City of Cape Town Metropolitan Municipality

- **Buyer:** City of Cape Town (CCT) — metropolitan municipality, various directorates (Energy: Electricity Generation & Distribution; Spatial Planning and Environment; Water and Sanitation; Solid Waste, etc.)
- **Kind:** Metro / local government (Municipal Finance Management Act + Municipal SCM Regulations regime; CIDB Standard Conditions of Tender used for construction works)
- **Packs sampled:** 10 — ocds-9t57fa-164090, ocds-9t57fa-164925, ocds-9t57fa-164091, ocds-9t57fa-164923, ocds-9t57fa-165567, ocds-9t57fa-164928, ocds-9t57fa-164924, ocds-9t57fa-164099, ocds-9t57fa-164118, ocds-9t57fa-165573
- **Date compiled:** 2026-08

---

## Submission channel & rules

Uniformly hard-copy, box-only submission — no electronic or dual-channel option observed anywhere in the sample. Every pack specifies a numbered "Tender Box" at the Civic Centre and an identical no-late-tender rule.

> "TENDER BOX : The Tender Document (which includes the Form of Offer and Acceptance) completed in all respects, plus any additional supporting documentation required, must be submitted in a sealed envelope with the name and address of the tenderer, the tender No. and title, the tender box No. and the closing date indicated on the envelope. The sealed envelope must be inserted into the appropriate official tender box before closing time." (ocds-9t57fa-164118, also verbatim in ocds-9t57fa-164090, -164925, -164091, -164923, -165567, -164928, -164924, -164099, -165573)

> "Telegraphic, telephonic, telex, facsimile, e-mail and late tenders will not be accepted." (ocds-9t57fa-164118, -165573; equivalent "(late tenders)." exclusion clause present in all packs, e.g. ocds-9t57fa-164090 line 677)

If a bid is too large for the box, the onus is explicitly placed on the tenderer to get alternative instructions from the Tender Distribution Office and still get it in before closing — the buyer does not accept blame for an overflow box:

> "If the tender offer is too large to fit into the abovementioned box or the box is full, please enquire at the public counter (Tender Distribution Office) for alternative instructions. The onus remains with the tenderer to ensure that the tender is placed in either the original box or as alternatively instructed." (ocds-9t57fa-164118)

Documents are only issued from the physical Tender Distribution Office for a R300 non-refundable fee, and CCT disclaims responsibility for addenda if a bidder gets the pack any other way: "Bidders who obtain documents through any means other than described herein, will not be known to the employer and may thus not receive tender notices and addendums." (ocds-9t57fa-164118)

Not observed in sampled packs: any e-submission portal, email lodging, or a "hard-copy governs over electronic copy" reconciliation rule (moot here since there is no second channel).

## Municipal-arrears / rates clause

Consistent window across every JSON-numbered pack with the SBD/MBD-style returnable schedule (not present in the two CIDB construction packs, which use a different declaration set): arrears of **more than 3 months** (not 90 days) on rates/taxes/municipal charges owed by the tenderer *or any of its directors/members/partners*, to CCT **or to any other municipality/municipal entity**.

> "2.4 Does the tenderer or any of its directors owe any municipal rates and taxes or municipal charges to the municipality / municipal entity, or to any other municipality / municipal entity, that is in arrears for more than three months?" (ocds-9t57fa-164090, -164925, -164091, -164928, -164924, -164099)

> "hereby acknowledges that according to SCM Regulation 38(1)(d)(i) the City Manager may reject the tender of the tenderer if any municipal rates and taxes or municipal service charges owed by the tenderer (or any of its directors/members/partners) to the CCT, or to any other municipality or municipal entity, are in arrears for more than 3 (three) months" (ocds-9t57fa-164090)

Distinctive twist: a separate returnable "**Schedule F.8: Authorisation for the Deduction of Outstanding Amounts Owed to the CCT**" makes the tenderer pre-authorise CCT to deduct any outstanding municipal debt directly from payments due under the contract, and requires disclosure of every municipal account number and whether each business address is "Inside the CCT municipal boundary" — present in all 8 non-CIDB packs sampled.

> "therefore hereby agrees and authorises the CCT to deduct the full amount outstanding by the Tenderer or any of its directors/members/partners from any payment due to the tenderer" (ocds-9t57fa-164090)

## B-BBEE treatment

No hard B-BBEE pre-qualification gate observed. CCT has moved to the Preferential Procurement Regulations (PPR) 2022 "**Specific Goals**" model rather than classic B-BBEE-status-level points: preference points (80/20 split up to R50m, 90/10 above R50m) are awarded against specific goals — Reconstruction and Development Programme (RDP)/HDI, promotion of Micro and Small Enterprises, Enterprise/Supplier and Socio-Economic Development spend, and Skills Development or Employee Share Scheme — with a B-BBEE certificate used only as one piece of supporting evidence, not as the scoring mechanism itself.

> "Preferences are offered to tenderers who tender in accordance with the Preferential Procurement Regulations and Regulations and the SCM Policy, tenderers are required to meet the HDI and/or RDP specific goals" (ocds-9t57fa-164118)

> "Table B2: Awards above R50 mil (VAT Inclusive) ... 1 Promotion of Micro and Small Enterprises 4 ... 2 Enterprise Supplier Development and Socio Economic Development 3 ... 3 Skills Development OR Employee Share Scheme 3 ... Total points 10" (ocds-9t57fa-164923)

One pack explicitly turns preferential procurement off entirely for a specialised professional-services bid: "Pre-qualification criteria for preferential procurement ... Preferential procurement is not applicable to this tender." (ocds-9t57fa-164923) — showing CCT will disable the preference system tender-by-tender rather than applying a blanket gate.

Not observed in sampled packs: a fixed minimum B-BBEE status level as a pass/fail eligibility gate (e.g. "must be Level 4 or better to be considered").

## Cure/condonation policy

Two-tier and mechanical, following the CIDB Standard Conditions of Tender verbatim in every pack:

- **Fatal (no cure):** a "material deviation or qualification" cannot be cured — the buyer will not let a bidder fix or withdraw it to become responsive. "Reject a non-responsive tender offer, and not allow it to be subsequently made responsive by correction or withdrawal of any material deviation or qualification." (ocds-9t57fa-164090)
- **Curable (buyer corrects mechanically):** arithmetic errors, decimal-point misplacements, and omissions in the Price Schedule are fixed by CCT using fixed governing rules — words govern over figures, the line-item total governs over the unit rate (and vice versa for gross decimal errors), and the total of prices governs over item prices — after which the tenderer is "asked to revise selected item prices ... to achieve the tendered total." If the tenderer won't accept the correction, CCT "consider[s] the rejection of a tender offer." (ocds-9t57fa-164090, §2.3.8)
- CCT retains explicit discretion to waive minor issues: "The CCT reserves the right to accept a tender offer which does not, in the CCT's opinion, materially and/or substantially deviate from the terms, conditions, and specifications of the tender documents." (ocds-9t57fa-164090)

Distinctive: a **"Standby Bidder"** mechanism appears in every sampled pack — CCT nominates a runner-up at award stage who can be awarded the contract without a fresh tender if the winning contract is later terminated for non-performance, effectively a pre-baked institutional workaround rather than a bidder-facing cure.

> "'Standby Bidder' means a bidder, identified by the CCT at the time of awarding a bid that will be considered for award should the contract be terminated for any reason whatsoever. ... the CCT may consider the award of the contract, or non-award, to the Standby Bidder in terms of the procedures included [in] its SCM Policy" (ocds-9t57fa-164090, -164925, -164091, -164923, -165567, -164928, -164924, -164099, -164118)

## Security/vetting requirements

Not observed in sampled packs: any post-award personnel vetting, security-clearance requirement, or integrity-pact signature requirement. What is consistently present is POPIA (Protection of Personal Information Act) consent/processing language baked into the tender conditions themselves, plus a dedicated Information Officer mailbox:

> "The Employer's Information Officer who is responsible for overseeing questions in relation to data protection may be contacted at via email Popia@capetown.gov.za." (ocds-9t57fa-164118, -165573, and all others)

> "that, under POPIA, the tenderer may request to access, confirm, request the correction, destruction, or deletion of a record of personal information about the tenderer ... that under POPIA, subject to applicable law, the tenderer also has the right to be notified of a personal information [breach]" (ocds-9t57fa-164090)

Standard national anti-corruption screening (not CCT-specific) is present via Schedule F.7 (MBD 8) — National Treasury Database of Restricted Suppliers / Register for Tender Defaulters checks and past 5-year fraud-conviction/contract-termination questions (ocds-9t57fa-164090, and consistently across the sample).

## Financial demands

- **Public liability insurance:** minimum **R20 million per single claim**, in the name of the Supplier, covering both Supplier and Purchaser. "Public liability insurances, in the name of the Supplier, covering the Supplier and the Purchaser against liability for the death of or injury to any person, or loss of or damage to any property, arising out of or in the course of this Contract, in an amount not less than [R20 million] for any single claim" (ocds-9t57fa-164090, -164925, -164091, -164923, -165567, -164928, -164924, -164099).
- Also mandatory: Motor Vehicle Liability Insurance (minimum "Balance of Third Party" with Passenger Liability Indemnity) and COIDA registration/Letter of Good Standing, evidenced via a prescribed pro-forma Insurance Broker's Warranty rather than freeform proof.
- **Audited financials:** required only where the tenderer is claiming Specific Goal preference points tied to turnover/expenditure/profit disclosures, not as a blanket eligibility gate — "the most recent (where applicable) audited financial statements to enable validation of ... Total Turnover ... Total Expenditure ... Total Profit," and "Companies who are required to be audited by legislation, must submit audited financial statements, not older than 12 months." (ocds-9t57fa-164091)
- **Performance/Advance Payment Guarantees:** required via prescribed pro-forma forms (C1.3 Form of Performance Guarantee, C1.4 Form of Advance Payment Guarantee) in the CIDB-format construction packs (ocds-9t57fa-164118, -165573); specific percentage not stated in the sampled text (page-referenced only, form content not captured in extract).
- Not observed in sampled packs: a specific bank confirmation-letter or credit-rating requirement independent of the insurance/guarantee pro-formas.

## Functionality norms

Functionality is scored as a separate gate before price/preference, with thresholds varying by tender (not a fixed house number):

- Minimum qualifying score 60/100 (ocds-9t57fa-164925, -164091)
- Minimum qualifying score 70/100 (ocds-9t57fa-164924)
- Minimum score 105 (scale not fully captured) (ocds-9t57fa-164923)
- Equipment/sample-based functionality demonstration used in at least one pack: "demonstration of the submitted sample(s) to illustrate the functionality, performance and compliance ... respond to technical questions from the evaluation committee." (ocds-9t57fa-164928)

> "Only those tenders submitted by tenderers who achieve the minimum score for functionality as stated below ... The minimum qualifying score for functionality is [60] out of a maximum of [100]." (ocds-9t57fa-164925)

Criteria style: individually scored by each Bid Evaluation Committee member then reconciled/interrogated as a panel, to two decimal places — "Where the scoring of functionality forms part of a bid process, each member of the Bid Evaluation Committee must individually score functionality. The individual scores must then be interrogated and ... Score financial offers, preferences and functionality, as relevant, to two decimal places." (ocds-9t57fa-164090)

## Distinctive kill rules / quirks

1. **Deduction-authorisation returnable (Schedule F.8):** every bidder pre-authorises the City to deduct outstanding municipal debt from any payment due — a leverage mechanism most municipal buyers don't formalise as a signed returnable schedule (ocds-9t57fa-164090 and 7 others).
2. **Standby Bidder nomination at award:** CCT names a runner-up at award time who can step into a terminated contract without a fresh tender — present in every sampled pack, construction and goods/services alike (ocds-9t57fa-164118, -164090, etc.).
3. **"Specific Goals" preference model, not classic B-BBEE points table:** points are earned via SME promotion, ESD/SED spend %, and skills-development/employee-share-scheme %, with B-BBEE certificates used only as supporting evidence — a materially different scoring shape from the generic B-BBEE-status-level table used by many other organs of state (ocds-9t57fa-164923, -164090).
4. **Arrears test reaches beyond CCT itself:** the "more than 3 months" arrears disqualifier is checked against debts owed to CCT *or to any other municipality/municipal entity in South Africa*, not just the buyer's own books (ocds-9t57fa-164090).
5. **Buyer explicitly disclaims addenda delivery for out-of-channel document collection:** obtaining tender docs any way other than the official Tender Distribution Office voids the buyer's obligation to notify that bidder of addenda (ocds-9t57fa-164118).
6. **Non-compulsory-but-strongly-recommended clarification meetings** are the norm rather than compulsory briefings, held via Teams/hybrid with dial-in numbers printed directly in the tender notice (ocds-9t57fa-164118, -165573).
7. Not observed in sampled packs: two-envelope (technical/price separated) submission, or a formal cybersecurity/ICT vetting annexure — despite one pack (ocds-9t57fa-164923) being a cybersecurity-professional-services tender.
