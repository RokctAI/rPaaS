# Sample Pack — TENDER 18-2025/26: Musina LM Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System (3 Years)

Musina Local Municipality (Limpopo) · MBD regime · closing **2026-05-11
11:00 — already passed at build date (retrospective sample)** · 80/20 ·
**no scored functionality stage** (Stage 1 admin + mandatory requirements
pass/fail, Stage 2 price + specific goals).

Bidder in all files: **Umzansi Infrastructure Group (Pty) Ltd — FICTIONAL
PROFILE FOR DEMO** (all identifiers deliberately fake; see top-level
README), extended for this bid with an equally fictional cloud
contact-centre capability described in `02-bid-no-bid.md`.

> **GROUNDING QUALITY — best of the set.** The complete official 65-page
> pack was fetched directly from the buyer's website
> (musina.gov.za/download/tender-18-2025-26-…, linked by the client) and
> carries a full text layer — no OCR needed, no registry intermediary, no
> derived returnables. Everything quoted in 01/02/04 is actual pack text.
> There is **no matching record in the `/opportunities` registry** (its
> seven Musina records are unrelated 2026-2027 RFQs), so closing date,
> evaluation method and returnables all come from the pack alone. The one
> caveat is temporal: the tender **closed three months before the build**,
> so the sample is a retrospective demonstration and the closed window is
> rendered as a fatal gate on the generated pack's warning page.

> **TERM NOTE (recorded neutrally).** Per client domain knowledge, Musina
> contract terms were believed to run 5 years. **This pack's own stated
> term is 3 years / 36 months** — title, ToR §1, pricing instruction
> §6(a) — and its pricing schedule is a Year 1/2/3 grid. First Musina
> pack on file; recorded as pack evidence, one data point not a norm.

## Files and provenance

| File | What it is | Provenance |
|------|-----------|------------|
| `01-requirements-checklist.md` | Pack-quoted returnables checklist, §5.1 mandatory requirements, two-stage evaluation with specific-goals split, critical criteria → kill-rule map, issued-forms vs fixture-set comparison, legacy/2022 preference contradiction | **MOCKED** (hand-written; grounded in quoted pack text). §6 rule-matching list is **GENERATED** by SDK `rules.rule_applies` (36 rules) |
| `02-bid-no-bid.md` | Gate pass/fail, mandatory-requirements outlook (no functionality threshold — N/A case), 3-year pricing vs pack schedule, specific-goals arithmetic (10/20), split merits/calendar recommendation (GO on merits / NO-BID, window closed) | **MOCKED**, except the 80/20 classification and the 70.48-point price example — **GENERATED** by SDK `scoring.py` |
| `03-bid-pack.html` | Printable pack, **MBD regime** (12 forms: MBD1, 2, 3.2, 4, 5, 6.1, 6.2, 6.4, 8, 9, 10, POPIA), **97.1% auto-fill (66/68)**, 49 red blanks, **3-gate warning page** (closed-window `[manual]` gate + GATE-RATES + bank-rating `[manual]` gate), MBD1 total-price face field filled from the linked 12-line 3-year quotation (**R2,573,750.00**; under MBD only the total reaches a form — the line-items table renders solely on the SBD3.x template, F-10) | **GENERATED** — verbatim `pack_builder.py` output. Profile/bid-context/quotation inputs **MOCKED** to the endpoint contract |
| `03-bid-pack.manifest.json` | Machine manifest | **GENERATED** (same run) |
| `04-pack-structure.md` | Assembly per the pack's own contents page and attachment rules (submit as a whole, no pages removed, attachments after the Council's price schedule, initial every page) | **MOCKED** (hand-written from quoted pack text) |
| `03-bid-pack.pdf` | Print-ready **A4 PDF render** of the generated pack (22 pages), for review/printing in submission format | **GENERATED** — direct headless-Chromium render of the SDK's HTML output, no content changes |
| `05-pricing-schedule.xlsx` | Excel pricing schedule laid out to the pack's own pages 11–12 grid: Once-Off / Monthly / Annual per Year 1–3 (flat-rated, no escalation formula in the pack), the 12-line once-off + monthly breakdown, per-unit call tariffs (variable, outside the fixed total) and the QTN-2026-00341 3-year total (R2,573,750.00 incl VAT), with live formulas | **GENERATED for this sample set, hand-built** — NOT SDK output (the SDK cannot model the pack's year-by-year grid, finding F-06); all values are the fictional mock bid; unit tariff rates are mock placeholders |

> **Submission-format note.** These files make the pack reviewable in
> submission format, but a real submission additionally needs wet-ink
> signatures (black ink, witnessed where the forms demand it), initials at
> the bottom of EVERY page (this pack's explicit rule), and certified
> copies of supporting documents on the buyer's OFFICIAL issued forms —
> submitted as a whole, no pages removed, into the Room 53 tender box. No
> digital render carries any of that (and this tender's window is closed —
> retrospective sample).

## What this sample shows

Three things new to the set. First, **full-pack grounding end-to-end**: for
the first time every gate, returnable and evaluation clause is quoted from
a complete official pack (fetched from the buyer's own site), so the
fixture-vs-reality comparison in `01-…md` §5 is exact — 4 of the pack's 9
returnable forms match SDK templates exactly (MBD 4/6.1/8/9), while the
buyer-authored Forms A–E (offer, signatory authorisation, legacy HDI
declaration, 1939-Ordinance local content, OHS s37(2)) have no fixture
representation (F-02), and the pack internally carries **two contradictory
preference frameworks** (pre-2011 HDI equity + PPR 2022 specific goals —
new finding F-12). Second, a **pack with no scored functionality stage**:
the correct `functionality_threshold` is "none", every §5.1 mandatory
requirement is a binary kill, and the SDK's single-pair functionality model
is simply not exercised — a negative case complementing F-05. Third, a
**fired deadline kill in a real timeline**: the tender closed before the
sample was built, and the generated warning page carries the closed-window
gate — the "late is dead" rule demonstrated on a real date rather than
hypothetically. GATE-POPIA again failed to attach (F-03) despite POPIA
compliance being explicit **specification text** here (§4(c), plus
SA-hosting and 18-month call-recording retention), the strongest POPIA
miss of the set. The pack's own Year 1/2/3 pricing grid is direct
pack-text evidence for the multi-year pricing gap (F-06) — though at 3
years, not the believed 5.

## Company-profile returnable — not applicable to this pack

Uniquely well-grounded answer, since the full 65-page pack is on file: it
lists no company-profile returnable. The page-2 "CHECKLIST OF
DOCUMENTATION TO BE ATTACHED" names only statutory documents (TCS PIN,
certified IDs, rates statements, financial statements, CSD report, "All
other documents as indicated in the General Conditions Document"), and
every §5.1 mandatory technical returnable (a)–(l) is a specific document —
solution proposal, tariff schedule, project plan, system description,
three references with appointment letters, risk plan, training plan, AFS,
bank rating letter, support documentation — none of which a marketing
profile satisfies. The generated company-profile artifacts for the same
fictional bidder live in [`../company-profile/`](../company-profile/) —
usable as unscored supporting material only; nothing is wired here.
