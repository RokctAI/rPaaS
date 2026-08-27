# Minimum Functionality Thresholds — Corpus Profile

Scanned 1200 corpus documents plus 37 deep-analysis extracts. 
Found an explicit minimum functionality threshold in **238 documents**.

- **Mode:** 70
- **Median:** 70.0
- **Range:** 36–100


## Distribution

| Threshold | Count | Share | Example ocids |
|---|---|---|---|
| 70 | 125 | 52.5% | acsa-power-retic-maint-rfq, hda-asbestos-monitoring-prt, mpofana-healthcare-panel |
| 80 | 30 | 12.6% | joburgtheatre-ahu-replacement, joburgtheatre-frozen-dry-goods, namakwa-dm-banking |
| 60 | 27 | 11.3% | dlrrd-cleaning-hygiene-kzn, limpopo-dsd-catering, mkhondo-task-work-study |
| 75 | 25 | 10.5% | dbsa-bulk-water-feasibility, fs-publicworks-eoi-qs, kokstad-franklin-roads |
| 65 | 10 | 4.2% | ocds-9t57fa-164104, ocds-9t57fa-164943, ocds-9t57fa-165180 |
| 36 | 9 | 3.8% | ocds-9t57fa-165538, ocds-9t57fa-165539, ocds-9t57fa-165540 |
| 50 | 5 | 2.1% | ocds-9t57fa-164986, ocds-9t57fa-165331, ocds-9t57fa-165842 |
| 83.3 | 1 | 0.4% | cge-wan-voip |
| 40 | 1 | 0.4% | ocds-9t57fa-164520 |
| 69 | 1 | 0.4% | ocds-9t57fa-164914 |
| 56 | 1 | 0.4% | ocds-9t57fa-165236 |
| 66.6 | 1 | 0.4% | ocds-9t57fa-165529 |
| 73 | 1 | 0.4% | ocds-9t57fa-165711 |
| 100 | 1 | 0.4% | ocds-9t57fa-165996 |

## Breakdown by buyer type

| Buyer type | Docs | Mode | Median | Values seen |
|---|---|---|---|---|
| municipality | 80 | 70 | 70.0 | {36: 9, 50: 1, 60: 8, 65: 2, 69: 1, 70: 44, 73: 1, 75: 4, 80: 9, 100: 1} |
| other | 47 | 70 | 70 | {50: 1, 60: 4, 65: 6, 70: 25, 75: 3, 80: 8} |
| SOE/statutory body | 43 | 70 | 70 | {50: 3, 56: 1, 60: 4, 65: 1, 66.6: 1, 70: 21, 75: 4, 80: 8} |
| (unknown) | 41 | 70 | 70 | {40: 1, 60: 6, 70: 17, 75: 11, 80: 5, 83.3: 1} |
| other public entity | 19 | 70 | 70 | {60: 4, 65: 1, 70: 13, 75: 1} |
| national/provincial dept | 5 | 70 | 70 | {60: 1, 70: 3, 75: 1} |
| education | 3 | 70 | 70 | {70: 2, 75: 1} |

## Recommended defaults

Most packs use a threshold of **70%** (mode; median 70.0). The market clusters on [70, 80] with a smaller tail at other values. Recommended defaults when generating or pre-screening bids:

- Default assumption when a pack is silent or ambiguous: **70%** of total functionality points.
- Treat 60% as the practical floor (common for catering, work-study, general services) and 80% as the strict ceiling (common for leases, financial services, and high-risk technical packs).
- Always check for per-criterion sub-minimums (e.g. key-staff minimums) — several packs disqualify on a single criterion even when the overall threshold is met.
- Caveat: values in the low tail (e.g. 36, 40, 50) are mostly raw point scores on non-100 scales (e.g. 36 out of 65 points ≈ 55%), not percentages; most 60-80 values are out of 100 and read directly as percentages.


*Generated 2026-08-18 from corpus2 regex scan + analysis JSON join. CSV: functionality-thresholds.csv*
