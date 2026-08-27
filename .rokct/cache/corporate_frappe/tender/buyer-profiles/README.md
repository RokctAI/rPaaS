# Buyer Quirk Sheets

Per-buyer quirk data extracted from the 2026-08 corpus of ~1,198 eTenders packs (plus the 37 deep-analysis extracts). Each sheet profiles one South African public buyer across the dimensions that decide bids in practice: submission channel rules, municipal-arrears windows, hard-copy/formality rules, B-BBEE treatment, cure/condonation tiers, security/vetting requirements, financial demands, functionality norms, and distinctive kill rules.

The five mock-sample buyers (findings F-11) additionally carry machine-readable `QUIRK-*` rules in [`../frappe/fixtures/tender_compliance_rules.json`](../frappe/fixtures/tender_compliance_rules.json) (rule_class `Buyer Quirk`, triggered by `institution_matches` on the cached OCDS buyer name) — those sheets list their rule codes.

These sheets are sample-derived, not exhaustive. **"Not observed in sampled packs" means the clause was silent in the packs we sampled for that buyer — it does not mean the buyer never uses it.** Always verify against the live tender document.

## Buyers profiled

| Sheet | Buyer | Most distinctive quirk (from the sheet) |
|---|---|---|
| [acsa.md](acsa.md) | Airports Company South Africa (ACSA) | Dual-channel bids where the physical Tender Box copy silently overrides the electronic one — skipping the physical drop is fatal even if the email arrived on time. |
| [atns.md](atns.md) | Air Traffic and Navigation Services (ATNS) | "Locality Footprint" is a fatal Stage 2 mandatory requirement, not a preference score — bidders must prove physical presence in the specific municipal/provincial area of performance. |
| [city-of-cape-town.md](city-of-cape-town.md) | City of Cape Town Metropolitan Municipality | Schedule F.8 deduction-authorisation returnable: every bidder pre-authorises the City to deduct outstanding municipal debt from any payment due. |
| [city-of-tshwane.md](city-of-tshwane.md) | City of Tshwane Metropolitan Municipality | Tippex/correction fluid on the price schedule is an automatic, named disqualifier — on top of a hand-completion-in-black-pen rule paired with e-portal-only submission. |
| [dept-tourism.md](dept-tourism.md) | Department of Tourism (national) | One-cluster/one-province lock-in with physical site visits to verify the claimed office address — no office at the stated address means disqualification. |
| [dws.md](dws.md) | Department of Water and Sanitation (DWS) | 100% local-content designation used as a hard specification gate (e.g. wood material) — below-threshold bidders need a dtic exemption letter, not just fewer points. |
| [ec-health.md](ec-health.md) | Eastern Cape Department of Health (ECDoH) | District-scoped locality points: preference is tied to the specific health district running the bid, and out-of-district bidders are told outright they cannot claim the points. |
| [eskom.md](eskom.md) | Eskom Holdings SOC Ltd | Silent-CPA default trap: submit no Contract Price Adjustment formula and pricing is locked fixed-and-firm for the entire multi-year contract term. |
| [ethekwini.md](ethekwini.md) | eThekwini Metropolitan Municipality | Dual-channel submission with hard-copy supremacy — an electronic JDE/ESP submission alone is never sufficient, and mismatched copies can invalidate the whole tender. |
| [mogale-city.md](mogale-city.md) | Mogale City Local Municipality | Handwritten-only, black-ink-only MBD forms: re-typed, scanned, or electronically completed documents are rejected, Tipp-Ex and erasable pens invalidate the bid. |
| [prasa.md](prasa.md) | Passenger Rail Agency of South Africa (PRASA) | Sworn Security Screening Form with full banking/director disclosure (bank account, director IDs, criminal-record declaration) submitted with the bid itself, not at award. |
| [sanral.md](sanral.md) | South African National Roads Agency (SANRAL) | State Security Agency vetting as a condition precedent to contract finalisation, plus contractor-run annual polygraph testing of deployed staff for the life of the contract. |
| [stats-sa.md](stats-sa.md) | Statistics South Africa (Stats SA) | Non-responsiveness trigger for slow replies: failing to meet a buyer-communicated (not pre-published) deadline on follow-up requests can void the quote. |
| [transnet.md](transnet.md) | Transnet SOC Ltd (incl. TNPA) | Sequential Post-Tender Negotiation cascade: if #1's price isn't "market-related," Transnet negotiates with #1, then #2, then #3 in order — a firm-holding #1 can lose the slot. |
| [ray-nkonyeni.md](ray-nkonyeni.md) | Ray Nkonyeni Local Municipality | Locality-based specific goals (RNM 10 / Ugu 5 / KZN 1, CSD-verified — not B-BBEE), plus black-ink completion and original-plus-ONE-copy on pain of disqualification. |
| [dffe.md](dffe.md) | Department of Forestry, Fisheries and the Environment (DFFE) | Phase-1 screening on a bound master document + identical USB copy + bidder-drafted table of contents. |
| [vaal-central-water.md](vaal-central-water.md) | Vaal Central Water | −20%/+20% financial tolerance band (out-of-band = eliminated), an R250m supplier-rotation threshold, and an unannounced 75% site-inspection phase. |
| [theewaterskloof.md](theewaterskloof.md) | Theewaterskloof Municipality | Advert-only registry grounding — no full pack exists, so "collect the official pack" is itself the first fatal gate (no QUIRK rules encoded). |
| [musina.md](musina.md) | Musina Local Municipality | Initial EVERY page at the bottom, submit-as-a-whole/no-pages-removed, attachments after the Council's price schedule, box hours 07:30–16:00, written-queries-only — and an explicit kill on emailed bids. |

## Companion artifacts (in [`../`](../))

- **[rules-table.md](../rules-table.md)** / **[rules-table.csv](../rules-table.csv)** — machine-readable rules table (65 rows: rule id, gate/kill/score type, trigger, severity, source packs).
- **[functionality-thresholds.md](../functionality-thresholds.md)** / **[functionality-thresholds.csv](../functionality-thresholds.csv)** — observed minimum-functionality-threshold distribution across the corpus (238 explicit thresholds; mode 70).
