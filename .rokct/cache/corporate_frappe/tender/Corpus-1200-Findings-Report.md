# Corpus-Expansion Findings: SA Tender Guide vs ~1,200 Packs

**Inputs:** `stats.json` (pattern counts over 1,200 docs), 15 qualitative delta reports (`group-0.json` ... `group-14.json`), guide `sa-tender-guide.md` (built from ~37 packs).
**Adjudication:** every contradiction claim used below was either cross-confirmed by 2+ independent group reports or spot-checked against the cited `corpus2/<ocid>.txt`. Spot-checks performed and confirmed verbatim: ocds-9t57fa-165894 (eThekwini hard-copy-governs), 164363 (SIU fax/email accepted), 165629 (Eskom B-BBEE pre-qualification disqualification), 165755 & 165539 (Mogale 50% / 55.4% functionality thresholds), 164297 (LDoH silence = acceptance of validity extension), 164869 (DWS "at liberty to qualify his bid"), 165115 (DBSA late-bid buyer-fault exception), 165524 (Kouga 1-month arrears), 164946 (OBP immediate disqualification for missing goal proofs), 164991 (TASEZ minimum B-BBEE level 3), 165894 ("FUNCTIONALITY will not be used"). No misreadings found among the checked claims; two claims were downgraded in severity during adjudication (see C-9, C-10 notes).

---

## (a) Headline verdict

**The guide substantially held up.** Its core architecture -- kill-rules first, universal-vs-conditional gates, evidence-beats-claims functionality, buyer-specific everything -- survives contact with a 32x larger corpus. No load-bearing recommendation reverses: "still submit without B-BBEE" remains right *for the preference-points case*, "never assume a cure window" remains right, the disqualification league table's top entries remain the right top entries.

**But it does not hold up unqualified.** The expansion surfaced a consistent failure mode: the 37-pack guide converted "most packs in a small sample" into "always/never/universal" language, and at ~1,200 packs nearly every one of those absolutes has real, verbatim-confirmed exceptions -- several on high-stakes rules (B-BBEE as a hard pre-qualification gate, the "always" evaluation pipeline, CIDB registration grace periods, the eThekwini dual-channel rule the guide states incorrectly for that named buyer). It also missed three genuinely common mechanisms that are now clearly corpus-wide, not curiosities: the PPPFA s2(1)(f) "objective criteria" award override, panel/framework two-stage evaluation, and post-scoring security/integrity vetting gates. **A v2 is warranted**: 10 confirmed contradictions and well over a dozen meaningful additions.

---

## (b) Corrected frequency numbers (from stats.json, n = 1,200)

Caveat: these are keyword-pattern matches over packs of very mixed depth (full bids, RFQs, notices), so they are *mention rates*, mostly lower bounds -- they don't overturn the guide's "universal in full formal packs" claims, but they do recalibrate several stated numbers.

| Guide claim | Original basis | Corpus at 1,200 | Verdict |
|---|---|---|---|
| CSD "essentially every full pack" | 30/37 | 792 (66% of all docs) | Holds for full packs; not literally universal across all doc types |
| SARS TCS PIN "every pack with bid conditions" | 33/37 | 687 (57%) | Holds directionally |
| B-BBEE affidavit route common | -- | 506 (42%) | Confirmed |
| 80/20 system | -- | 807 (67%); 90/10: 609 (51%); R50m threshold cited: 649 (54%) | Both systems routinely co-quoted -- supports the "deferred determination" warning |
| "Roughly half the corpus holds a briefing" | -- | compulsory 435 (36%) + non-compulsory 82 (7%) = ~43% | Holds; compulsory:non-compulsory ~ 5:1 |
| Bid validity "60-120 days" | -- | Of 482 packs stating a figure: 90d=186 (mode), 120d=155, 60d=46, 180d=31, 30d=28, 150d=6, 365d=5, <=28d=16 | **Needs widening: 30-180 typical span, mode 90; tails to 365** |
| Two-envelope "a minority (mostly SOE/DFI)" | -- | 70 (5.8%) | Confirmed minority; but municipal examples exist (see C-10 note) |
| CIDB grading (construction) | -- | 263 (22%); most-demanded grades cluster at 1GB-2GB and low grades generally | Confirmed; add: low-grade tenders dominate volume |
| GCC contract | -- | 597 (50%) vs NEC 42 (3.5%) vs JBCC 34 (2.8%) | GCC far more dominant than the guide's NEC/GCC pairing implies; FIDIC also appears (group-5) |
| SBD 6.2 local content "most packs mark N/A" | -- | SBD 6.2: 28 (2.3%); designated-sector language: 364 (30%) | Holds |
| Ink/handwriting kill "about half" | -- | black-ink pattern 210 (17.5%); initial-each-page 117 (10%) | League-table rank stands but "about half" likely overstated; treat as "recurring, buyer-specific" |
| Bank guarantees / bid security barely headlined | -- | bank_guarantee flag 309, bid_security_deposit flag 282 | More prevalent than the guide's passing treatment suggests |
| Electronic submission | -- | email 576 (48%), portal/electronic 242 (20%), tender box 563 (47%), fax mentions 149 (nearly all "will NOT be accepted") | Email is now the single most-cited channel -- guide's "municipal = physical box" heuristic still directionally right |

---

## (c) Confirmed contradictions

**C-1. B-BBEE is NOT always a soft gate.**
- *Guide (S3.1):* "everywhere in the corpus, missing it costs you the 10 or 20 preference points, never the bid."
- *Corpus:* Eskom Standard Conditions cl. 3.17 (165629, verified): where B-BBEE level is a *pre-qualification criterion*, missing proof at closing "will be disqualified." TASEZ (164991, verified): minimum B-BBEE level 3 required, certificate sits in the pass/fail Stage-1 administrative table. OBP (164946, verified): missing specific-goals proof "will be an immediate disqualification." Conversely, some packs award zero B-BBEE points at all (uMzimkhulu 164912, KZN EDTEA 164970) and one states preferential procurement "is not applicable" outright (CoCT 164923).
- *Fix:* the zero-points-only rule holds for B-BBEE *as a preference claim*; it fails where the pack uses B-BBEE as a pre-qualification/administrative gate. "Still submit the bid" advice must carry this check.

**C-2. The evaluation pipeline is not "always" compliance -> functionality -> price.**
- *Guide (S5):* "The pipeline is always..."
- *Corpus:* DBSA professional-services RFP (165115) runs responsiveness -> price/preference -> risk & objective criteria, with no scored functionality. WCG Health 3-year catering bid (164261): no functionality anywhere. Full CIDB municipal construction packs state "FUNCTIONALITY will not be used" (165894, verified; 164766). Panels run functionality-only at bid stage with price deferred to per-order RFQs (see N-2).
- *Fix:* "usually, where functionality is scored at all" + explicit instruction to check the Tender Data functionality clause even in large formal bids.

**C-3. CIDB grading is not universally an "active at close, do not proceed" gate.**
- *Guide (S1.3, S3.2):* absolute earliest gate; inactive = invalid.
- *Corpus:* Eskom (165629, 165418, 165874) and Joe Gqabi DM (165711): bidders "capable of being so registered within twenty-one (21) working days from the closing date" are eligible; proof of application suffices at closing, registration due by award. The 21-working-day CIDB cure explicitly exceeds the general 5-day cure window in the same Eskom pack.
- *Fix:* keep kokstad-style zero tolerance as the default assumption, but tell readers to check the eligibility clause for a registration grace period before self-eliminating.

**C-4. Functionality threshold range is wrong at the floor.**
- *Guide (S5.1):* "roughly 60% to over 80% ... with 70% the mode."
- *Corpus (verified):* Mogale City 15/30 = 50% (165755) and 36/65 = 55.4% (165539, 165541/42/44/46/51 -- recurring template); KwaDukuza minimum 40 points (164187). Verdict: range runs roughly **40-83%**, with 70% still the mode for formal bids; municipal panel/RFQ-style tenders regularly sit at 50-55%.

**C-5. eThekwini dual-channel rule is misstated for the named buyer.**
- *Guide (S7.2):* "hard copy and electronic copy must be identical -- a mismatch invalidates the offer (eThekwini)."
- *Corpus (165894, verified):* "a tender offer will only be deemed valid if the 'hard copy' submission has been made. The 'hard copy' submission will be the governing submission / ruling version." That is a precedence rule, not identical-or-invalid. ERWAT (165128) similarly: electronic optional, hard copy governs.
- *Fix:* correct the named example; reframe as "check whether the pack runs identical-or-invalid or hard-copy-governs."

**C-6. "Silence equals exclusion" on validity extensions is not universal -- the default runs in both directions.**
- *Guide (S7.2/S9F).*
- *Corpus:* Limpopo DoH (164297, verified): "the department will consider the non-response as an acceptance of the extension." eThekwini SCM Policy cl. 21.2 (165894): validity auto-extends 12 months unless the bidder objects in writing. Eskom (165629): agreeing to extend forbids modifying the tender.
- *Fix:* always respond in writing, but check which way the silence-default runs -- silence can bind you to a stale price rather than exclude you.

**C-7. Late submission has narrow, real exceptions at one sophisticated buyer.**
- *Guide (S2 rank 1):* "zero tolerance ... Universal."
- *Corpus:* DBSA (165115, verified): late bid may be accepted where lateness "was caused by the DBSA," box access was denied, or a major incident occurred -- sole discretion. Keep the rule; add the footnote (never rely on it).

**C-8. Fax/email submission is not always fatal.**
- *Guide (S2 rank 8, S7.2).*
- *Corpus:* SIU (164363, verified): "Faxed and emailed tender documents will be accepted." A genuine minority-of-one against 149 "fax will NOT be accepted" mentions -- keep the kill-rule, add the caveat that channel rules are per-pack even here.

**C-9. Qualified bids are not always incurable poison.**
- *Guide (S2 rank 12):* "non-responsive, cannot be cured."
- *Corpus:* DWS (164869, verified): "should it be deemed necessary ... the Bidder is at liberty to qualify his bid." Single-source and older boilerplate -- downgraded to a caveat, not a reversal: default remains "never qualify."

**C-10. Municipal rates arrears threshold is not a flat 3 months/90 days.**
- *Guide (S3.2).*
- *Corpus:* Kouga (165524, verified): arrears "for more than 1 (one) month" triggers rejection. Also: some buyers demand the clearance only from the recommended bidder (165711), not every bidder at submission. Fix: state 1-3 months as a buyer-specific range and check when it bites.

Adjacent corrections folded into the edit list rather than counted as separate contradictions: "firm prices only" vs issued SBD 3.2 *non-firm* schedules with mandatory escalation options (164297, 164104); MBD1 "write the total price on the form" vs two-envelope MBD1s instructing the opposite (164989); CIDB clarification cut-off "typically five working days" vs packs setting 3-4 days or overriding the CIDB default in Tender Data (164775, 164770, 165894, 165711); "assume briefing compulsory for construction" vs CIDB packs with no briefing at all (164770); "blank = invalid" vs Mnquma's blanks-default-to-N/A (164442); "uninitialled correction = kill" vs graduated consequence regimes (JW 165643, ERWAT 165128); "two-envelope = mostly SOE/DFI" vs municipal examples (165593, 164989).

---

## (d) Genuinely new material worth adding

**N-1. PPPFA s2(1)(f) "Objective Criteria" award override -- the biggest omission.** Confirmed independently at PPECB, TNPA, Johannesburg Water, TASEZ, DBSA, CSIR, Eskom, SANRAL (groups 1, 2, 4, 13, 14): a named post-scoring stage that can pass over the top-ranked bidder for prior poor performance with that buyer, litigation against the buyer, supplier rotation, financial-ratio risk, insolvency/business rescue, or director fraud charges. Winning on points does not guarantee award; the guide currently implies it does.

**N-2. Panel/framework two-stage mechanics.** Recurring across municipal and SOE packs (groups 2, 6, 9, 10, 12, 13): functionality-only gate to join a panel (sometimes no price submitted at all), then per-order RFQ mini-competitions at 80/20 among panelists, cascades to next-ranked on decline, ongoing performance-penalty/greylisting regimes, one-area limits and leased-equipment cross-checks (Johannesburg Water). Changes the bid-cost calculus entirely; the guide's "panels" bullet covers only pricing viability.

**N-3. Post-scoring security/integrity vetting gates.** SIU Internal Integrity Unit + SSA vetting "irrespective of the points scored" (164363, 164839); SANRAL SSA screening; Transnet CONFIDENTIAL/SECRET/TOP SECRET clearance for staff and subcontractors; DBSA PEP/Procure checks; SAPS SAP-91 original fingerprints for National Key Point work; SA-citizen-only personnel clauses (DHA, BMA). None of this is in the guide.

**N-4. New mandatory returnable form types.** POPIA consent/processing form (construction, municipal, SOE -- near-cross-sector); DPIP/FPPO politically-exposed-persons declaration (SANRAL Form A5, Transnet -- "tender may be rendered invalid" if omitted); branded Integrity Pacts additional to SBD 9 (Gauteng Treasury, Eskom, Transnet); litigation-history disclosure (SANRAL Form A8); GCC/SCC "ACCEPT ALL" tick-box as an independent kill (164297); MBD 2 original tax clearance certificate (with the original-only TCC rule now confirmed at multiple buyers, not just mpofana); Certificate of Single Tender Submission.

**N-5. Multiple-bid / common-interest disqualification.** Submitting more than one bid (solo or via JV) voids all submissions; JVs sharing directors/shareholders with another bidder are ineligible (eThekwini 165894, SANRAL 164220, Eskom 165874). Absent from the league table.

**N-6. Mogale City 2% "Corporate Social Responsibility" levy on non-local winners** -- deducted from every payment, with its own signed declaration returnable. Appears verbatim across ~9 packs in the corpus (one buyer, many tenders). Worth one bullet as the exemplar of locality *levies* (cost) vs locality *points* (scoring).

**N-7. Zero-in-any-criterion auto-disqualification.** "A score of zero (0) in any criteria will result in automatic disqualification, even if the minimum ... threshold is met" -- recurring Mogale template plus per-criterion minimums set equal to the maximum (165541). Stricter than the guide's sub-threshold warning.

**N-8. Income-generating/leasing tenders invert the price formula** -- Ps = 80/90 x (1 + (Pt-Pmax)/Pmax), highest acceptable offer wins (165524, 165529); plus the whole PPP/concession pack type (draft 25-year operator agreements with marked-up clauses, no SBD returnables) that the guide's framework doesn't cover.

**N-9. VAT deeming and forced registration.** Buyers deem prices above a threshold (R1m Stellenbosch/Mogale, R2.3m CWDM) VAT-inclusive regardless of what the bidder wrote; non-vendors whose win would push turnover past R1m must price VAT in and register with SARS within 21 days of award; RFQs often default to VAT-*exclusive* if silent (164946). Also most-favoured-customer clauses (Transnet), hard price ceilings (SAMRC), no-arithmetic-correction buyers (PPECB), price-declaration forms that govern over the schedule, and reverse e-auctions (Eskom: submit the entire tender price-free).

**N-10. Pack-type taxonomy is incomplete.** RFI (market sounding -- no returnables, but opt-in registration needed to receive addenda) and EOI (ranging from non-binding market test to a full three-phase scored pipeline) both appear repeatedly; the guide's bid-vs-RFQ binary needs a third and fourth category. Also: SOE RFQs with full functionality gates confirm and extend the guide's "label is unreliable" warning beyond construction.

**N-11. Assorted confirmed mechanics:** CIDB CSDG/CPG gazetted goals (as low as 5%, auto-triggering at value/duration/grade thresholds) and the 2024 B.U.I.L.D. programme; FIDIC as a third contract family; 3+ evaluator averaging on the 0/20/40/60/80/100 scale (CIDB PN#9); addenda that rewrite functionality weights; sub-R1m contracts substituting 5% payment-reduction for the performance guarantee (and 21-day guarantee windows, flat-Rand guarantees); Transnet 10%-of-contract penalty for undisclosed subcontracting; consent-gated-by-default subcontracting as a fourth stance plus 100%-pass-through bans; withdrawal-after-acceptance liability equal to the re-procurement price gap; portal specifics (30MB Transnet, 4MB/file Sasria, zip *required* at DBSA vs banned at Eskom, alphanumeric filenames, PDF-only, cloud-links rejected at one buyer and required at another); complaint/objection fees and the Transnet Ombudsman; document fees R300-R2,306 (wider both ways than R500-R1,150); transport-sector EMEs barred from the affidavit route; startup carve-outs from AFS requirements (Eskom PI score/ITA34C).

---

## (e) EDIT LIST for guide v2

| # | Section | Old text (gist) | New text |
|---|---|---|---|
| 1 | 3.1 | "B-BBEE ... everywhere in the corpus, missing it costs you points, never the bid" | "...in the great majority of packs. **Exception:** where the pack lists the B-BBEE certificate/level inside a pass/fail pre-qualification or administrative-compliance table (Eskom cl. 3.17-style; TASEZ demands minimum Level 3), missing or expired proof disqualifies outright. Check which table the certificate sits in before relying on the still-submit rule. Also: some specific-goals tables award zero points for B-BBEE at all -- read the buyer's table." |
| 2 | 5 (opener) | "The pipeline is always: compliance -> functionality -> price" | "The pipeline is usually: ... But a sizeable minority of full formal bids -- including multi-year service bids and CIDB construction packs -- run no functionality stage at all ('Functionality will not be used'), and DBSA-style RFPs score price first with a pass/fail risk review after. Check the Tender Data's functionality clause explicitly; never infer it from pack size or sector." |
| 3 | 5.1 | "Thresholds run roughly 60% to over 80% ... 70% the mode" | "Thresholds run roughly 40% to over 80% -- 70% remains the mode for formal bids, but municipal panel/RFQ-style tenders regularly set 50-55% (Mogale 15/30, 36/65) and one sits at 40. Read the number; a sub-60% bar is not a typo." |
| 4 | 5.1 (new bullet) | -- | "**Zero anywhere can kill:** some buyers disqualify for a zero on ANY criterion or sub-criterion even after the overall threshold is met, and some per-criterion minimums equal the criterion maximum (full marks or dead). Check for this wording separately from the overall threshold." |
| 5 | 1.3 / 3.2 | CIDB "active and in good standing at close ... do not proceed" | Keep as default, add: "Some buyers (Eskom, Joe Gqabi DM) accept bidders 'capable of being registered within 21 working days' -- proof of application at closing, registration by award. Check the eligibility clause for a grace period before self-eliminating; note the CIDB cure clock can be longer than the pack's general cure window." |
| 6 | 7.2 | "Dual-channel buyers (eThekwini): hard copy and electronic must be identical -- a mismatch invalidates" | "Dual-channel buyers split two ways: identical-or-invalid at some, versus a precedence rule at others -- eThekwini and ERWAT declare the hard copy the governing/ruling version if the two differ (and at eThekwini the bid is invalid without the hard copy even if uploaded). Check which regime the pack states." |
| 7 | 7.2 / 9F | "Answer any validity-extension request in writing -- silence equals exclusion" | "Answer in writing regardless -- but check which way the silence-default runs: at most buyers silence = exclusion, at Limpopo DoH silence = acceptance, and eThekwini's SCM policy auto-extends validity 12 months unless the bidder objects. Silence can bind you to a stale price. Also: agreeing to extend can bar any modification of your tender (Eskom)." |
| 8 | 2 (rank 1) | "Late submission ... Universal (zero tolerance)" | Add footnote: "One buyer (DBSA) reserves discretion to accept a late bid where the lateness was the buyer's own fault, box access was denied, or a major incident occurred. Never plan on it." |
| 9 | 2 (rank 8) + 7.2 | fax/email = dead at physical buyers | Add: "A rare exception exists (SIU accepts faxed and emailed tenders) -- channel rules are per-pack even here; and packs can contradict themselves on the channel itself (advert says portal-only while boilerplate still describes a bid box -- add 'submission channel' to the S1.4 contradiction sweep)." |
| 10 | 2 (rank 12) | "Qualified bid ... cannot be cured" | Add: "(a rare pack expressly permits qualifying the bid where an alteration is necessary -- DWS boilerplate -- but treat 'never qualify' as the default)." |
| 11 | 1.4 | "bid validity (60-120 days...)" | "bid validity -- mode 90 days; 30-180 days all common (120 nearly as common as 90; 180 calendar or business days at SOEs/metros; 30 at small RFQs; outliers to 365). Some packs ask YOU to state a validity. If two figures appear, price the longer and clarify in writing." |
| 12 | 1.4 | clarification cut-off "(CIDB packs typically five [working days])" | "Read the pack's own clause every time: CIDB packs run 3-5 working days, the Tender Data frequently overrides the standard five, the bidder-question cut-off and the addenda-issuance cut-off can be two different dates, and some buyers anchor the window to the briefing date, not the closing date. Diarise each separately." |
| 13 | 1.1 | Two pack types (formal bid / RFQ) | Add third and fourth: "**RFI** -- market sounding, no returnables, but register interest or you won't receive addenda/the later closed process. **EOI** -- ranges from non-binding market test (Eskom) to a full three-phase scored pipeline; judge by content, exactly as with the RFQ label. And SOE 'RFQs' can carry full scored functionality gates (Transnet crane repair, SABC) -- the label warning is not construction-specific." |
| 14 | 3.2 | "Arrears over 3 months/90 days ... = disqualification" | "Arrears threshold is buyer-specific -- 90 days at some (Kokstad), one month at others (Kouga, incl. any other municipality's arrears). Some buyers require the clearance only from the recommended bidder, not at submission. Check the certificate's own wording and when it bites." |
| 15 | 6.3 (new bullet) | -- | "**The 'Objective Criteria' override (PPPFA s2(1)(f)):** many buyers (Transnet, Eskom, SANRAL, DBSA, CSIR, PPECB, Johannesburg Water...) reserve a named post-scoring stage that can pass over the top-ranked bidder: poor track record with that buyer, litigation against the buyer, supplier rotation, financial-ratio risk analysis, insolvency/business rescue, director fraud charges, or lookback windows (18 months post-termination at DBSA). Winning on points is necessary, not sufficient. Related: post-scoring security/integrity vetting (SIU/SSA, SANRAL screening, Transnet clearances, fingerprints for National Key Points) can also override a winning score -- flag security-adjacent buyers at go/no-go." |
| 16 | 6.1 or new 6.5 | "Panels and rate contracts: estimated quantities not guaranteed" | Expand into a panel/framework sub-section: functionality-only panel entry (sometimes no price at panel stage), per-order RFQ mini-competitions at 80/20 among panelists, cascade to next-ranked on decline, ongoing performance-penalty/greylisting regimes, one-area/lot caps, leased-equipment cross-checks against other bidders, and exclusion for repeatedly ignoring RFQ invitations. |
| 17 | 6.1 (VAT bullet) | "Resolve the VAT basis ... evaluated total almost always VAT-inclusive" | Add: "Several buyers DEEM prices above a threshold (R1m-R2.3m) VAT-inclusive regardless of what you wrote -- the total stays fixed and an exclusive-priced bidder absorbs the 15%. Non-vendors whose win would push turnover past R1m must price VAT in and register with SARS within ~21 days of award. Simple RFQs often default to VAT-EXCLUSIVE if silent. Check the pack's default-if-silent and deeming clauses, not just inclusive/exclusive labels." |
| 18 | 6.1 + 8 | -- (locality only as points) | Add: "Locality can also be (a) a hard eligibility gate ('only bidders residing within X will be considered'), (b) a scored functionality criterion, and (c) a post-award LEVY -- Mogale City deducts 2% of every payment from non-local winners, with a signed acceptance declaration as a returnable. Price it; don't just score it." |
| 19 | 6.3 | Ps formula presented as universal | Add: "For disposal/leasing/income-generating tenders the formula inverts -- highest acceptable offer scores full points (Ps = 80/90 x (1 + (Pt-Pmax)/Pmax)). And 'best and final offer' negotiation rounds mean the submitted price is not always the evaluated price. Award cascades to the next-ranked bidder on decline or delivery default at several buyers -- 2nd place stays live past award." |
| 20 | 4.0 / 4.4 / 9B | Form catalog | Add the new returnables: POPIA consent form (cross-sector, mandatory at multiple buyers); DPIP/FPPO declaration (SANRAL/Transnet -- omission can invalidate); buyer-branded Integrity Pact IN ADDITION to SBD/MBD 9; litigation-history form (SANRAL A8); GCC/SCC 'ACCEPT ALL' tick-box (failure = disqualification); Certificate of Single Tender Submission; MBD 2 original tax clearance (original-only TCC now confirmed at several buyers -- reframe mpofana as a recurring older-template trait); SBD/MBD 3.2 method-of-pricing form (mandatory firm/non-firm option selection -- blank = not considered; and note SBD 3.2 non-firm schedules with escalation/ROE formulas exist, so soften 'firm prices only' to 'firm unless the pack issues a non-firm schedule'); MBD 6.4 local-content bonus points; third-party sourcing declaration with unconditional undertaking; lot/field tick-box tables (untick = disqualified). |
| 21 | 2 (tail) + 3.2 JV | -- | Add: "One bid per entity: submitting twice (solo or via JV) voids ALL your submissions, and JVs sharing directors/shareholders with another bidder are ineligible (eThekwini, SANRAL, Eskom). Check related-company exposure before two group companies bid the same tender. Also: buyer-specific cooling-off bans for ex-employees/board members (SABC: 12 months; 5 years if dismissed)." |
| 22 | 3.3 | banned / capped / mandatory | Add two stances and three mechanics: "consent-gated by default (GCC boilerplate: no subcontracting without prior written consent)" and "100% pass-through banned (Eskom)"; the boilerplate cap reads 25% OR 30% depending on the pack -- read the number; Transnet penalises undisclosed subcontracting up to 10% of contract value; CIDB CSDG/CPG gazetted goals trigger automatically at value/duration/grade thresholds and can be small (5%); mandatory-quota relief mechanisms exist (Engineer-approved motivated application); mandatory 30% thresholds can bite from as low as R4m (KwaDukuza). |
| 23 | 3.4 / 6.1 | "5-10% performance guarantee within about 14 days ... plus 10% retention" | "5-10% (or a flat Rand sum -- check) within 14-21 days; on contracts under ~R1m the 'guarantee' is often a 5% payment-reduction retention instead of a bond, and retention runs 5-10%. Read the security clause, not the rule of thumb. Add: some SOE master agreements carry most-favoured-customer price-matching with termination rights; some buyers refuse ALL arithmetic corrections (PPECB: submitted total is final); a separate Price Declaration Form can govern over the schedule on mismatch; withdrawal after acceptance can cost you the price gap to the next-ranked bid." |
| 24 | 7.1 / 7.2 | briefing + submission logistics | Briefing: "assume compulsory for construction until proven otherwise -- but some CIDB packs hold no briefing at all, and notice headers can say 'non-compulsory' while the body says 'compulsory': clarify in writing; some buyers publish an explicit grace period (doors close +10 min)." Submission: add concrete portal traps (30MB/upload Transnet, 4MB/file Sasria with all-schedules-required, zip REQUIRED at DBSA vs banned at Eskom, alphanumeric filenames only, PDF-only buyers, cloud-transfer links banned at one buyer and required at another -- with link-expiry reconfiguration duties at SABC); samples packaged separately from bid documents; broken CD/USB risk is the bidder's; complaint/objection fees and the Transnet Ombudsman (R5m threshold, bad-faith complaints risk blacklisting); English translations required for foreign-language documents; document fees run R300-R2,300+, not R500-R1,150; the handwritten-only rule is a recurring municipal template (Mogale, multiple packs) and can be scoped to just the BoQ -- while at least one buyer expressly permits digital completion, so check rather than assume either way. |

24 edits. Items 1-7 correct confirmed contradictions; 8-14 fix overstated absolutes/ranges; 15-24 fold in the new material.

---

## Bottom line

The guide's skeleton, priorities, and tone survive. What must change is (1) the word "always" -- nearly every instance now has a verbatim counterexample; (2) two named-buyer facts stated incorrectly or too strongly (eThekwini dual-channel, B-BBEE-soft-gate); and (3) three missing mechanisms (objective-criteria override, panel mechanics, security vetting) that a bidder relying on the guide would be genuinely blindsided by. That clears the bar for a v2 comfortably.
