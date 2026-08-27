# Buyer Quirk Sheet: Theewaterskloof Municipality

**Buyer:** Theewaterskloof Municipality (06 Plein Street, Caledon 7230, Western Cape; the registry record spells it "Theewaterkloof")
**Kind:** Municipality
**Packs sampled:** 0 full packs — 1 advert-level registry record only, ocds-9t57fa-165555 (COR 01/2026/27, Support, Maintenance, Development and Hosting of a Website, to 30 June 2029)
**Source:** [`../mock-samples/cor-01-2026-27-twk-website/01-requirements-checklist.md`](../mock-samples/cor-01-2026-27-twk-website/01-requirements-checklist.md)
**Date:** 2026-08

> **GROUNDING NOTICE.** No full tender pack for this buyer exists in the
> registry — the only source is the ~1.7KB advert record (description,
> closing, briefing flag, contact, advert link). Everything beyond §1 is
> DERIVED from the SDK's MBD regime fixtures and the guide's municipal
> defaults. **No `QUIRK-*` rules are encoded for this buyer** (findings
> F-11 encodes only pack-quoted quirks, and none exist here); collecting
> the official pack is itself the first fatal gate on any bid
> (GATE-PACK-COLLECT fires from the Advert-Only source-record class,
> findings F-08). Rewrite this sheet the day a full pack is collected.

---

## What the advert record states (the complete grounding)

- "COR 01/2026/27 – SUPPORT, MAINTENANCE, DEVELOPMENT AND HOSTING OF A
  WEBSITE FOR THE THEEWATERSKLOOF MUNICIPALITY FROM DATE OF APPOINTMENT TO
  30 JUNE 2029"
- Tender type "Request for Bid(Open-Tender)" → full municipal returnable
  spread expected (MBD regime)
- Closing 2026-09-18 12:00 at 06 Plein Street, Caledon → physical
  submission expected; channel rules to be confirmed from the pack
- Briefing: "No" per the record — re-verify from the official pack
- Category "Administrative and support activities"

## Expected municipal returnables (DERIVED, not pack text)

MBD 1/4/6.1/8/9 spread (templates generate); municipal rates clearance for
company AND every director (GATE-RATES fires from the MBD regime; WC
municipalities are strict); no arrears beyond threshold (KILL-19); CSD/TCS/
CIPC/defaulters/state-employee universal gates; B-BBEE certificate or
sworn affidavit (points evidence); MBD5 + AFS only above R10m — does not
apply at the ≈R2.18m five-year offer.

Website-specific returnables to expect (none modelled generically —
captured per bid via custom returnables, findings F-02/F-07): portfolio of
comparable municipal sites, web/hosting team CVs, hosting infrastructure
and data-residency spec, backup/DR and uptime SLA commitments,
security/patching regime, exit/handover terms. POPIA exposure is high on a
website/hosting contract but DERIVED, not confirmed.

## Functionality norms

Unknown — the advert names no evaluation method. Corpus base rate
(n=238): municipal mode **70**; any bid records
`functionality_threshold: 70 (ASSUMED)` until the pack is collected.

## Term & escalation

Advert term runs to 30 June 2029 (≈33 months if appointed late 2026); per
client domain knowledge municipal website support tenders mostly carry a
5-year maintenance term with CPI-linked escalation — the mock quotation
models the 5-year CPI-escalated schedule (mock 5.0% p.a., R2,179,056.00
total). PRICE-MULTIYEAR-ESC attaches over 12 months (findings F-06).

## Distinctive kill rules / quirks

None quotable — advert-only grounding. The record's one distinctive fact
is itself the quirk: **an open municipal website tender published with no
pack content in the registry**, making "collect the official pack" the
first fatal gate (GATE-PACK-COLLECT).
