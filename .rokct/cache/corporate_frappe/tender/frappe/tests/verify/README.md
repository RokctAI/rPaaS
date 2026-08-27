# TenderAssist verification suites (standalone, frappe-free)

Each suite stubs frappe in-memory, loads the REAL modules from this repo
(endpoints exec'd with the composer `{app_name}` placeholder substituted)
and prints one PASS/FAIL line per check plus a final `N/N checks passed`.
Run them from anywhere - paths resolve relative to this directory:

```sh
python3 tender/frappe/tests/verify/verify_wave1.py       # wave-1 fixes (F-03/F-04/F-10/F-12)
python3 tender/frappe/tests/verify/verify_wave2_pr_a.py  # functionality sections (F-05)
python3 tender/frappe/tests/verify/verify_wave2_pr_b.py  # pricing/returnables/capabilities (F-06/F-02/F-07)
python3 tender/frappe/tests/verify/verify_wave3.py       # enrichment gate + ingestion (F-08/F-14)
python3 tender/frappe/tests/verify/verify_pr_c.py        # quirks, seeding, lints, dispatch (F-11/F-13)
python3 tender/frappe/tests/verify/verify_pr_d.py        # deterministic pack parsing (F-02 full)
python3 tender/frappe/tests/verify/verify_pr_e.py        # F-02 CALIBRATION round + F-15(b) hook
python3 tender/frappe/tests/verify/verify_o4_smoke.py    # O-04 e2e smoke: attach/attest REAL engine artifacts
python3 tender/frappe/tests/verify/verify_suitability.py # FEEDBACK 1.2 automated suitability scoring
python3 tender/frappe/tests/verify/verify_market_context.py # awards-derived market-context tables + payload block
python3 tender/frappe/tests/verify/verify_renewal.py     # Renewal Watch: ledger math, duration parsing, radar endpoint
python3 tender/frappe/tests/verify/verify_preference_delivery.py # opt-in personalized get_relevant_tenders (legacy path byte-identical)
python3 tender/frappe/tests/verify/verify_pricing_bands.py # bid-time pricing bands: formatting, fallback chain, get_my_bids enrichment
python3 tender/frappe/tests/verify/verify_competition.py # low-competition finder: field-narrowness scoring, profile crossing, ranked endpoint
python3 tender/frappe/tests/verify/verify_buyer_dossiers.py # buyer dossiers: awards-derived per-buyer stats, dossier endpoint
python3 tender/frappe/tests/verify/verify_hygiene.py # 2026-08-24 assessment fix/hygiene items (catalog_base_url seam, structured telemetry)
python3 tender/frappe/tests/verify/verify_manifest.py # manifest<->code agreement: 72 aliases <-> 24 whitelisted endpoints, both directions
python3 tender/frappe/tests/verify/verify_notify.py      # notification seam (plan #14): channel registry, opt-in gate, call-site equivalence
python3 tender/frappe/tests/verify/verify_deadline_watch.py # bid deadline watcher (plan #10): closing window, open-work detection, briefing reminders
python3 tender/frappe/tests/verify/verify_dispatch_ledger.py # plan #11 dispatch checksum ledger: sha256 of sent bytes, append-only records, attest-time hashing
python3 tender/frappe/tests/verify/verify_award_ledger.py # award-outcome ledger: own-outcome aggregation, ocid award matching, caveats
python3 tender/frappe/tests/verify/verify_compliance_calendar.py # unified compliance calendar: four-stream assembly, ordering, watch-item semantics
python3 tender/frappe/tests/verify/verify_suitability_drift.py # scheduled suitability drift report: fixed-persona corpus run, snapshot storage, determinism
```

`verify_market_context.py` additionally re-runs the deterministic table
generator (`tender/frappe/tools/build_market_context.py`) against the
committed awards dataset (`tender/awards-dataset/awards_only.csv`) and
fails when the committed `src/control/compliance/data/market_context.json`
drifts from a fresh rebuild.

These live in the tree (rather than a session scratchpad) per the findings
doc's F-02 follow-up note: the claimed check counts must be re-runnable by
anyone. `data/` carries the read-only catalog snapshots `verify_wave3.py`
checks against, plus `pr_b_baseline_686850c/` - the verbatim pre-PR-B tree
(PR #37's merge commit) that `verify_wave2_pr_b.py` compares against for
its byte-identity checks, committed so the suite needs no git history and
runs on shallow clones (`git show` is only used for the snapshot-vs-git
drift check, which SKIPs when history is unavailable; `PR_B_BASE_REF`
still overrides the baseline to a git ref for ad-hoc comparisons).

`verify_pr_e.py` additionally verifies against the REAL 65-page Musina
buyer PDF (TENDER 18-2025/26) when available: set `MUSINA_PACK_PDF` to the
downloaded pack, or drop it at `data/musina-18-2025-26-pack.pdf`. The PDF
is deliberately NOT committed - fetch it from the musina.gov.za download
page quoted in `tender/mock-samples/18-2025-26-musina-helpdesk/README.md`.
Without it the real-PDF section prints SKIP lines (not failures).

`verify_o4_smoke.py` is the O-04 end-to-end smoke for the F-15(b) studio
hook: capture -> attach -> attest -> gate-clears -> SATISFIED BY GENERATED
ARTIFACT, driven through the real endpoint/gate/builder modules. Set
`O4_BUSINESS_PROFILE` / `O4_COMPLIANCE_LOG` to a real StartupOS
`compile --only business_profile` output pair (engine:
RokctAI/The-Rokct-Protocol `core/utils/startup_os`) for the real-files
run; those files are deliberately NOT committed. Without the env vars the
suite runs against the small committed stand-ins
`data/o4_business_profile.md` / `data/o4_compliance_log.md` (clearly
marked SYNTHETIC) and prints SKIP lines for the engine-provenance checks.
Both modes must be all green.

The suites are named `verify_*.py`, not `test_*.py`, on purpose: they are
standalone scripts with their own harness, not pytest collectables.

Every suite sets `sys.dont_write_bytecode = True` at the top of its
harness (O-05), so in-tree runs leave no `__pycache__/` directories under
`tender/frappe/src/`.

## Bench-only tests are NOT the verification harness (O-06)

The bench tests beside this directory (e.g. `tests/test_bid_pack.py`)
import through the composer's literal `{app_name}` placeholder, so they
only run inside a composed bench - they cannot run in this repo, and a
check that exists ONLY in a bench test is unverifiable here (the F-02
follow-up's "68/68 not re-runnable" problem). Any future
finding-verification must extend these `verify_*` suites - frappe stubbed
in-memory, the real modules loaded with the placeholder substituted - so
the claimed counts stay re-runnable by anyone. A bench test may duplicate
a verify check; it must never be the only place a finding is verified.
