# Buyer Quirk Sheet: Musina Local Municipality

**Buyer:** Musina Local Municipality (Private Bag X611, Musina 0900, Limpopo)
**Kind:** Municipality
**Packs sampled:** 1 — TENDER 18-2025/26 (Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System, 3 years; official 65-page pack fetched from musina.gov.za — the best-grounded sample of the set)
**Source:** [`../mock-samples/18-2025-26-musina-helpdesk/01-requirements-checklist.md`](../mock-samples/18-2025-26-musina-helpdesk/01-requirements-checklist.md)
**Date:** 2026-08

Note on sample composition: single-pack sheet, but from the complete
official pack with a full text layer (no OCR, no registry intermediary).
"Not observed" below means silent in this one pack.

**SDK quirk rules encoded from this sheet (findings F-11):**
`QUIRK-MUSINA-PAGEINIT` (Fatal), `QUIRK-MUSINA-WHOLE-DOC` (Fatal),
`QUIRK-MUSINA-ATTACH-ORDER` (Curable), `QUIRK-MUSINA-BOX-HOURS` (Curable),
`QUIRK-MUSINA-WRITTEN-QUERIES` (Curable), `QUIRK-MUSINA-TOLLFREE`
(Curable) — all auto-attach via `institution_matches: ["musina"]` in
`fixtures/tender_compliance_rules.json`.

---

## Submission channel & rules

Tender box only: sealed envelope with service description + bid number,
deposited at the Reception Office **Room 53** (cnr Irwin and Scholtz), box
open **07:30–16:00 weekdays** (→ `QUIRK-MUSINA-BOX-HOURS`). Brochure §3.4:
"Tenders submitted by facsimile, telex, telegram or e-mail WILL NOT BE
CONSIDERED" — an explicit email kill (KILL-16/KILL-01 family; the SDK's
F-13 dispatch endpoint refuses full-pack email unless a pack explicitly
allows it, and this buyer is the canonical counter-example).

Paper formality:
- "NB: INITIAL EVERY PAGE OF THE TENDER DOCUMENT AT THE BOTTOM"; "ALL
  PAGES OF THE BID DOCUMENT MUST BE INITIALED AND SIGNED WHERE REQUIRED"
  (→ `QUIRK-MUSINA-PAGEINIT`).
- "BID DOCUMENT MUST BE COMPLETED IN INK"; brochure §3.2: signed in
  **black ink**, "Failure to sign ALL relevant documents will invalidate
  the bid" (KILL-07/KILL-10).
- Brochure §3.6: "The complete Bid Documents … must be submitted in the
  same order and no part thereof must be removed"; contents page: "DO NOT
  REMOVE ANY PAGES" (→ `QUIRK-MUSINA-WHOLE-DOC`; KILL-13 family).
- Attachments go "at the back of the official bid document. (i.e. After
  the Councils price schedule)" (§3.9; → `QUIRK-MUSINA-ATTACH-ORDER`).

**Enquiries are written-only**: "Telephonic queries/enquiries will not be
entertained" — technical queries to the Acting Manager: ICT, SCM queries
to the Manager SCM (→ `QUIRK-MUSINA-WRITTEN-QUERIES`; the F-13
correspondence tier is the matching SDK surface).

## Municipal-arrears / rates clause

"Copy of municipal rates and taxes statement of account not older than
three months **for all directors and for the company**" — GATE-RATES
matches almost word-for-word and fires from the MBD regime.

## B-BBEE / preference treatment

80/20; specific goals HDI 10 / women 4 / disability 3 / youth 3 (PPR 2022
MBD 6.1). **Pack self-contradiction:** the same pack carries the pre-2011
HDI equity framework (Form C, "points out of 20") and a 1939-Ordinance
local-content/SABS certificate (Form D) — only MBD 6.1 scores, but every
framework's form must be completed (WARN-PREF-CONFLICT lint, findings
F-12).

## Financial demands

AFS demanded from **every** bidder regardless of value (page-2 checklist +
§5.1(i) "Recent Audited financial statements (previous 3 financial
years)") — value-decoupled, GATE-MBD5's >R10m trigger correctly does not
fire at the ≈R2.57m offer; manual row. "Service Provider Banking Rating
[A to C] not older than 3 months" (§5.1(j)) — no fixture rule.

## Functionality norms

**No scored functionality** — two-stage evaluation: Stage 1 administrative
compliance + mandatory requirements (pass/fail eliminations, the §5.1
list), Stage 2 price + specific goals. The SDK models this as
`functionality_mode: "No scored functionality"` (findings F-05) — the
useful negative case against the corpus mode of 70.

## Distinctive kill rules / quirks

1. **Initial every page at the bottom** (→ `QUIRK-MUSINA-PAGEINIT`).
2. **Submit as a whole — no pages removed, same order**
   (→ `QUIRK-MUSINA-WHOLE-DOC`).
3. **Attachments after the Council's price schedule**
   (→ `QUIRK-MUSINA-ATTACH-ORDER`).
4. **Tender-box hours** 07:30–16:00 weekdays, Room 53
   (→ `QUIRK-MUSINA-BOX-HOURS`).
5. **Written queries only** (→ `QUIRK-MUSINA-WRITTEN-QUERIES`).
6. **Retention of the existing toll-free call-centre number** in the
   helpdesk ToR (→ `QUIRK-MUSINA-TOLLFREE`).
7. Explicit email-submission kill (§3.4) — the channel-gating evidence for
   the F-13 dispatch design.
8. Multi-year official pricing grid: Year 1–3 Once-Off/Monthly/Annual
   columns + per-unit call tariffs (findings F-06; 3-year fixed portion
   R2,573,750.00).
