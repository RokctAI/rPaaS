# Auto-Submission for TenderAssist — Feasibility Report & Architecture Proposal

**Date:** 2026-08-18 · **Prepared for:** Ray
**Evidence base:** four research lenses in `scratchpad/autosubmit/` — corpus-evidence (37 analyzed packs), etenders-portal (verified portal + official e-Submission manual), legal-practical (statute, case law, pack quotes), other-channels (provincial/metro/SOE survey) — plus the verified state of the protocol repo and control app.

> **Decision note (2026-08-23, owner decision — Ray):** eTenders eSubmission sits behind a CAPTCHA (see §2, hard blocker 4), so **portal auto-submission is off the table**. Auto-submission is viable **only for tenders that allow submission by email**. Accordingly, the portal/eSubmission automation branch of this report — including the assisted eTenders driver in Stage 3 — is marked **NOT VIABLE** below, and the recommended architecture is re-scoped to the email-channel pipeline only. The portal research and the channel census in §1 are retained unchanged as evidence; superseded passages are annotated, not deleted.

---

## 1. The landscape: most SA tenders still cannot be submitted online

**Finding: only about a third of tenders in our corpus are electronic-only (at most ~43% offer any electronic path, counting the 4 hybrids), and just ~6% of tenders on the national portal support in-portal eSubmission. The physical tender box is still the single largest channel — a bare majority of our corpus.**

Across the 37 tender packs we have fully analyzed:

| Channel | Count | Share |
|---|---|---|
| Physical box/envelope only (electronic explicitly refused or absent) | 19 | 51% |
| Electronic only (portal 7, email-based 5) | 12 | 32% |
| Dual/hybrid (both channels) | 4 | 11% |
| Unspecified (submission volume missing from pack) | 2 | 5% |

A consistent signal at national scale: the eTenders portal's public JSON API (`/Home/TenderOpportunities/?status=1`) returned 1,833 currently advertised tenders on 2026-08-18, of which only **111 (~6%) have `eSubmission: true`**. For the other 94%, etenders.gov.za is an advertisement board only — submission happens per the bid document (physical box, email address, or the buyer's own e-procurement system; in our corpus the box is the most common of these). Note the 6% measures in-portal eSubmission specifically, not the physical/electronic split.

The electronic third is itself fragmented. Of our 12 electronic-only packs, 5 are email-based (ACSA, Necsa, two departmental RFQs; the fifth, DBSA, is a OneDrive upload link issued after an email request — not plain SMTP) and 7 are portals — but **six different portals**: National eTenders eSubmission, SALGA Supplyflow, Eskom e-Tendering, Transnet eSupplier, PURCO SA, City of Tshwane. The other-channels survey adds Western Cape ePS, Gauteng TendaSwift, Cape Town SAP e-Services, and eThekwini's JD Edwards system. None advertises a supplier-facing submission API. "Auto-submit everywhere" is therefore really N bespoke browser automations plus one email pipeline.

Two corpus caveats matter for classification logic. First, the **"OR ONLINE" boilerplate trap**: the SBD1/MBD1 template phrase appears in at least 5 physical-only packs that simultaneously refuse electronic bids, and conversely two electronic packs carry physical CIDB sealing boilerplate that the project-specific notice overrides. Channel detection must implement precedence (tender-specific notice > standard conditions), not keywords. Second, hybrids are the worst case: eThekwini requires *both* a hard copy in the box *and* an identical upload, with the hard copy ruling — automating the electronic half alone discharges nothing.

Sample-size honesty: 37 packs, SA public procurement, Aug–Oct 2026 closings. The 51/32 split is indicative for our market segment, not universal — the 6% figure is a one-day full snapshot of everything advertised on the national portal (which does not carry every SA tender — some municipal and provincial-platform tenders sit outside it) and points the same direction.

## 2. What can and cannot be automated

**Finding: submission-adjacent work (assembly, validation, deadline management) is automatable across all channels; the final submission act is automatable only for email tenders, ~~semi-automatable for portals~~ *(2026-08-23 decision: portal automation NOT VIABLE — CAPTCHA)*, and not automatable at all for the physical majority. Several blockers are legal or physical, not technical.**

**Hard blockers (cannot be automated away):**

1. **The tender box.** 19/37 packs require a sealed, labelled envelope physically inside a specific box before a clock-strict deadline ("tender box locked exactly at 12:00 noon"; proof of posting ≠ proof of delivery). Some add originals-plus-sealed-copies, USB copies inside the envelope, or signing a register next to the box. The last mile here is a human or courier, full stop.
2. **Wet-ink signatures.** ECTA permits e-signatures in general, but does **not compel an organ of state to accept them** — and several buyers expressly refuse: Namakwa DM deems any electronically signed returnable *non-responsive*; Nkomazi bars electronic signatures outright; Nkomazi and Joburg Theatre require black-ink pen and forbid retyping, and several packs (eThekwini, CIDB-form packs) require initials on every page. A "print the e-signed PDF" shortcut fails at these buyers.
3. **Commissioned affidavits and certified copies.** The B-BBEE EME/QSE sworn affidavit (the single most common oath item — ~80% of the legal lens's ~30-pack sample offer it as the EME/QSE route, though only 7 corpus JSONs explicitly flag commissioner involvement) and "certified within 90 days" copies require physical presence before a Commissioner of Oaths (*FirstRand v Briedenhann*: "in the presence of" means physical presence as the rule — the court there condoned virtually commissioned affidavits as substantial compliance, but that was judicial discretion; SCM committees apply strict responsiveness checking, so virtual commissioning cannot be relied on). Even fully electronic portals accept only *scans* of these physically created artefacts. The ECTA s18(1) commissioner-with-AES route exists in law but no evaluator practice supports relying on it.
4. **Portal access controls and terms.** eTenders login requires CSD credentials plus an image CAPTCHA — a deliberate anti-bot gate; circumventing it would create arguable ToS and Cybercrimes Act exposure (untested: no public eTenders ToS was found — terms may exist behind login — and there is no case law on point). CSD terms make credentials personal, confidential, signature-equivalent. Eskom reportedly gates login with an OTP sent to cellphone and email, and its sites returned HTTP 403 to our automated fetches; Cape Town mandates "log in as yourself"; Transnet requires bids from the bidder's own company profile.
5. **Zero-tolerance non-compliance law.** *Dr JS Moroka v Betram* (SCA): peremptory tender conditions cannot be condoned. A bot-caused defect — wrong channel, missing stamp, late upload, a wrong tick-box on SBD4 — is non-condonable disqualification (the evaluator has no power to forgive it; the bidder's only recourse is court review), and ECTA s20 attributes the bot's actions to the bidder (with fraud/blacklisting consequences for false declarations). Eskom adds a resubmission trap: a failed re-upload near closing voids the earlier good submission.
6. **Samples:** only boilerplate references in our corpus; low relevance today.

**What is automatable, with high confidence:**

- **Discovery and channel classification** — the eTenders JSON API is open (no auth), including the `eSubmission` flag and document blobs; every surveyed portal publishes adverts openly (though Eskom's WAF returned 403 to our automated fetches, so its adverts may need an assisted or whitelisted fetch path).
- **Pack assembly** — merging, naming, and ordering documents to the pack's exact rules (one PDF per eSubmission checklist heading; ACSA's 4MB×4 email split; Eskom's 500MB/doc, 4GB, no-zip, folder taxonomy).
- **Prefill and validation** — SBD/MBD form filling from company data, cross-checking every checklist item, flagging contradictory instructions for human resolution.
- **Compliance-artefact inventory** — affidavits, certifications, tax PINs and bank letters as tracked assets with expiry windows (12 months / 90 days / 30 days), with scheduled human commissioning trips before they lapse.
- **Deadline discipline** — targeting T-24h (Transnet's own advice), never T-0.
- **Email submission end-to-end** — the one channel with no login, no CAPTCHA, no ToS; risk reduces entirely to document correctness. Still gated by human approval (see §3).
- ~~**Assisted portal submission** — software stages everything; an authorised human logs in, passes CAPTCHA/OTP, and clicks Submit, then verifies status is "Submitted" (not "Pending").~~ *(NOT VIABLE — 2026-08-23 decision: the CAPTCHA gate rules out the portal automation branch, assisted mode included. Portals get Stage 1/2 outputs plus a runbook only; retained here as research.)*

## 3. Staged architecture

**Finding: auto-submission should land as three stages that extend the existing enrichment → sidecar → checklist flow, each shipping value independently, with Stage 3 ~~(assisted portal submission) deliberately capped at human-gated automation~~ *(re-scoped 2026-08-23: Stage 3 automation is the email channel only; portal branch NOT VIABLE — CAPTCHA)*.**

The submission channel becomes a first-class classification alongside the Pillar 1 requirements work: the enrichment pipeline writes a `submission` block into the per-tender `{id}_requirements.json` sidecar (channel: `physical | email | portal | hybrid | unknown`; portal identity; address/email; closing timestamp; format rules; precedence notes where boilerplate conflicts were auto-resolved, flagged `needs_human_review` when confidence is low). The eTenders `eSubmission` boolean gives a free, authoritative signal for the ~6% it covers; everything else comes from pack text with the precedence rule (specific notice > boilerplate) baked in.

### Stage 1 — Pack assembly automation (build now)

*What:* generate the complete submission bundle from the Bid Checklist Items plus the requirements sidecar. For every tender in `Preparing`, produce: one correctly named PDF per checklist/requirement heading (portal-ready), a merged master PDF in prescribed order, channel-specific outputs (email attachments pre-split to size caps; for physical packs a print manifest, envelope labels with the exact box address and tender number, copies/USB instructions, and a courier cut-off computed back from closing), and a coverage report of missing items.

*Where:* protocol repo — new `tenders/submission/` module (assembler + channel rules), templates and outputs under the existing `response_kits/` directory, one bundle folder per tender. Control app: extend **Bid Checklist Item** with `artifact_path` and `included_in_bundle`; add a "Bundle ready" indicator on **Tender Bid**. No new status needed yet.

*Data needed:* requirements sidecar, checklist state, a company document library (registration docs, B-BBEE affidavit, tax PIN letter — each with `valid_until`). No credentials.

*Risk controls:* the assembler never invents content — it only packages artefacts a human placed; expired compliance artefacts hard-block bundle completion; contradictory channel instructions block with `needs_human_review`.

### Stage 2 — Prefill and validation (next)

*What:* auto-fill the repetitive SBD/MBD returnables (SBD1, SBD4, SBD6.1, bidder details) from a canonical company profile, producing *draft* forms; validate the whole bundle against the sidecar (all compulsory items present, formats/sizes within channel limits, signatures/commissioning present where required, dates in window); maintain the compliance-artefact expiry calendar with proactive "commissioning trip" tasks.

*Where:* protocol repo `tenders/submission/prefill/` and `validate/` (this is Pillar 4 drafting applied to returnables, feeding Pillar 3 audit). Control app: new **Company Profile / Compliance Artifact** doctype(s); per-item validation status surfaced in the frontend checklist; a new **Ready to Submit** state between `Preparing` and `Submitted` on Tender Bid, reachable only when validation passes *and* a named human has attested each auto-filled declaration.

*Risk controls (legal, per ECTA s20 / SBD4 fraud exposure):* every prefilled form is watermarked DRAFT until a human reviews and signs; the attestation (who approved which form, when) is stored on the Tender Bid as an audit trail. Wet-ink-required packs route to print-sign-scan tasks, never e-signature.

### Stage 3 — Assisted submission (later; human gate is permanent by design)

> *Re-scoped 2026-08-23 (owner decision): Stage 3 automation is the **email channel only**. The eTenders eSubmission driver below is NOT VIABLE (CAPTCHA) and is retained struck-through as research; all portals — eTenders included — fall under the "other portals" treatment (runbooks, no drivers).*

*What:* per-channel dispatch from a `Ready to Submit` bid.

- **Email channel (5/12 electronic packs — the beachhead; note one of the 5, DBSA, is a request-a-OneDrive-link flow, not plain SMTP):** system composes the exact email(s) — address, subject-line format, split attachments — and holds them in a queue. A human opens the tender in the frontend, sees a diff-style preview, and clicks **Approve & Send** per tender. Post-send, delivery receipt archived to the bid. *(2026-08-23: this is now the whole of Stage 3 automation — the only viable auto-submission channel.)*
- ~~**eTenders eSubmission (the only reusable portal):** driver automation (Playwright) that navigates to the tender, selects the MAAA entity, uploads the pre-assembled per-heading PDFs, and clicks Confirm & Proceed — but the **human performs login and CAPTCHA in the same visible browser session, reviews the populated checklist, and personally clicks "Submit now."** The system then verifies "My Responses" shows **Submitted** (green), screenshots it, and archives the proof; `Pending` is treated as failure and alarms. We never solve CAPTCHAs programmatically and never run headless-unattended.~~ *(NOT VIABLE — 2026-08-23 decision: eSubmission is behind a CAPTCHA; portal auto-submission is off the table. eTenders now gets the runbook treatment below.)*
- **Other portals (Eskom, Transnet, SALGA, Tshwane, metros — and, per the 2026-08-23 decision, eTenders eSubmission too):** no automation — Stage 1/2 outputs plus a step-by-step per-portal runbook generated from the sidecar. ~~Add drivers only per-buyer when volume justifies it and that portal's terms have been read and cleared.~~ *(2026-08-23: per-buyer portal drivers are off the table with the rest of the portal branch.)*
- **Physical (the 51%):** Stage 3 here is courier orchestration — booking, label generation, delivery tracking, and a "confirm deposited in box" human check-in — not submission automation.

*Where:* email dispatch in protocol repo `tenders/submission/dispatch/` (portal drivers no longer in scope per the 2026-08-23 decision); approval gate, queue, and proof-of-submission records in the control app (`Ready to Submit → Submitting → Submitted`, with `submission_proof` attachments); Approve-button UX in the frontend claim/checklist flow.

*Credentials:* *(retained for the record — with the portal branch NOT VIABLE, no portal credential handling ships; the email channel needs none of this beyond the sending mailbox.)* CSD/portal credentials are the bidder's own, personal, signature-equivalent. They live in the bidder's own secret store (or are typed by the bidder at session time), are never stored in the repo, control app database, or logs, and are never used by unattended jobs. Third-party credential custody is off the table — CSD terms (credentials unique, confidential, signature-designated) make it at least arguably a confidentiality breach; the analysis is untested in court, but it is not a risk to build a product on.

*Risk controls (non-negotiable):* (1) **no submission of any kind without an explicit, logged, per-tender human approval** — this is a legal control (attribution, *Moroka* zero tolerance), not a UX preference; (2) hard T-24h target with escalating alerts, and a **freeze window** near closing that blocks automated re-uploads (the Eskom null-and-void trap); (3) success is defined only by the channel's own confirmation state, captured as evidence; (4) any pack contradiction or validation failure de-escalates the bid back to `Preparing`.

## 4. Recommendation and open questions for Ray

**Recommendation *(as amended by the 2026-08-23 owner decision)*: build Stage 1 now, Stage 2 immediately after, and scope Stage 3 to ~~email + eTenders-assisted only~~ **the email channel only**. Do not pursue portal submission automation in any form — assisted included: it is blocked by CAPTCHA/OTP, sits in untested ToS/credential-terms territory, is legally attributable to the bidder, and addresses at most a third of the market anyway.** The durable value is upstream: for 100% of tenders (including the physical majority) TenderAssist can own assembly, prefill, validation, compliance-artefact expiry, and deadline logistics — the places where bids are actually lost. The submission click stays human, per tender, forever; frame this to users as a feature ("you always pull the trigger"), because it is also our liability firewall.

**Open questions:**

1. **CSD/MAAA scope:** are we operating for one bidder entity or many? Multi-entity (bureau model) sharpens the credential and "own-profile" concerns — Transnet and Cape Town rules may prohibit us acting on a client's profile at all. Legal review needed before any bureau-style Stage 3.
2. **Terms review:** eTenders' logged-in ToS (not publicly visible) and each SOE portal's click-wrap must be read before shipping even assisted drivers. Who does that review, and do we get written comfort? *(2026-08-23: moot for now — no portal drivers, assisted or otherwise, are in scope.)*
3. **Courier partner:** for the 51% physical channel, do we integrate a courier API (and which), or leave dispatch as a checklist task with deadlines?
4. **Missing-volume tenders:** 2/37 packs lacked the submission volume entirely — should the enrichment pipeline auto-fetch missing tender-data volumes, and hard-block bidding until channel is known?
5. **Sidecar schema ownership:** the `submission` block extends the Pillar 1 `{id}_requirements.json` contract — sign-off needed from the Pillar 1 owner so requirements and submission enrichment don't fork.
6. **Compliance-artefact service:** the affidavit/certification expiry calendar could be a standalone offering (it applies to every tender, every channel). Product decision: bundle or separate?
