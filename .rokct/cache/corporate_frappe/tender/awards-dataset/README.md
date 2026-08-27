# eTenders Awards Dataset

`awards_only.csv` — a flat per-award table of **32,589 award rows** (plus
header) extracted from the public South African eTenders OCDS release corpus
(https://ocds-api.etenders.gov.za), snapshot **2026-08-20**.

sha256: `5e57844559671e18a103853019f665018b1f5219f59574c8bc50fed718f8a0d5`

The file is committed byte-identical to the extract (CRLF row terminators
preserved via the local `.gitattributes`); `ocid` values are byte-exact copies
from the source JSON — no trimming or case changes — so they are safe to use
as exact join keys.

## Purpose

Score-calibration join against the active card corpus:

- **Primary join key:** exact `ocid`.
- **Fallback key:** buyer name + tender number (for cards missing an ocid).

See [tender/Award-Outcomes-Research.md](../Award-Outcomes-Research.md) for the
full analysis built on this dataset.

## Provenance

- Corpus snapshot fetched 2026-08-20 by sequential tender-ID enumeration
  (`ocds-9t57fa-1 .. 166500`): **163,321 releases**.
- **32,589 releases (19.95%) carry an award block**; this feed emits exactly
  one award per awarded release, single supplier each — hence one CSV row per
  award.
- 32 tender IDs returned persistent HTTP 500 at fetch time and are excluded
  from the corpus (not re-fetched).
- Suspicious amounts are **flagged, never dropped** — see `amount_flag` below
  (9,123 zero-amount awards, 825 non-zero amounts < R100, 330 amounts
  > R10bn).
- This is public procurement data from the public OCDS feed; it contains no
  confidential or personal client data.

## Columns

| column | description |
|---|---|
| `ocid` | OCDS open contracting ID, byte-exact from source (primary join key) |
| `release_id` | release identifier, byte-exact from source |
| `buyer` | buyer (procuring entity) name |
| `title` | tender title |
| `category` | `tender.mainProcurementCategory` |
| `province` | from `tender.province` (present on every release in this feed) |
| `tender_value` | advertised tender value (`tender.value.amount`) |
| `closing_date` | `tender.tenderPeriod.endDate` |
| `award_id` | award identifier |
| `award_status` | award status (all `active` in this snapshot) |
| `award_date` | always empty — field structurally absent from this feed |
| `award_value` | awarded amount (all ZAR) |
| `currency` | award currency (all `ZAR`) |
| `supplier_names` | `\|`-joined names of all suppliers on the award |
| `supplier_ids` | `\|`-joined supplier IDs |
| `n_tenderers` | always empty — field structurally absent from this feed |
| `contract_start` | always empty — field structurally absent from this feed |
| `contract_end` | always empty — field structurally absent from this feed |
| `amount_flag` | data-quality flag: `zero` (amount = 0), `missing`, `lt_R100` (0 < amount < 100), `gt_R10bn` (> 1e10); empty when the amount looks normal |

Structurally absent fields (award date, contract period, number of tenderers)
were extracted anyway but are always null in this feed, so the
award-vs-closing lag distribution is not computable from this corpus.

## The rest of the dataset

Only the flat CSV is committed here. The full per-release extract
(`awards_extract.jsonl`, all 163,321 rows — one per release, releases without
awards included so coverage is measurable) and the extraction, coverage,
analysis, and renewal-radar scripts live in the project workspace dataset
directory `etenders-awards/` — too large for the repo.
