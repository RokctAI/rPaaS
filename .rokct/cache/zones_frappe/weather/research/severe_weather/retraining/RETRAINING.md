# RETRAINING.md — the human-triggered re-tuning discipline

This folder holds the tooling that turns outcome-ledger evidence into a
**candidate** detector configuration. Read this before running anything.
It is written for a reader who does not know machine learning; the short
version is:

> **Nothing retunes itself. A human runs the harness, a human reads the
> report, and the live system only changes when a human merges a PR.**

## The pieces, in plain language

- **The detector** is a set of hand-inspectable rules ("if moisture stays
  above X for Y hours, raise a heads-up") stored in one JSON file:
  `detector/detector_config_tuned.json`. This file is what actually runs in
  production. It is frozen: its SHA-256 fingerprint is recorded in
  `detector/BACKTEST.md`, so any change to the file is detectable.
- **The frozen bars** are the acceptance thresholds in `PLAN.md` (POD, FAR,
  and median lead time per event class), committed *before* any tuning
  began. Every report compares against those numbers; the numbers never
  move to meet the results.
- **The outcome ledger** is the "Severe Weather Outcome" table the live
  system fills in daily: for every ended episode it records whether extreme
  weather really followed (a *hit*), or nothing happened (evidence of a
  *false alarm*), and it separately records disaster-grade extremes that
  arrived with no episode at all (a *candidate miss*). The ledger is
  write-only evidence — nothing consumes it automatically.
- **The admin report** (`api.get_retraining_report`, control plane, System
  Manager only) reads that ledger and says, per event class: here is what
  we observed, here is the frozen bar, and here is the plain verdict —
  *meeting bar*, *below bar*, or *insufficient data*. This report is how a
  human decides whether a re-tune is even worth considering.
- **The harness** (`retrain.py`, this folder) is the offline tool that
  actually searches for better rule settings and grades the result.

## When to consider re-tuning

1. The admin report says a class is **below bar** (or a real-world failure
   makes you doubt the current settings), **and**
2. the ledger holds **at least 20 judged outcomes for that class** (the
   harness enforces this; `--force` overrides it, and should be a conscious
   exception you can defend in the PR).

A thin ledger is the normal early state. "Insufficient data" means exactly
that — wait, don't tune. Tuning against a handful of outcomes just teaches
the detector the noise of those few weeks.

## The tune-on-one-era / prove-on-another rule

The central trap in this kind of work is grading your own homework: if you
adjust the rules until they look good on some data, then measure them *on
that same data*, the score is meaningless — the rules have partly memorized
the answers. The guard against that is time:

- **Era A (earlier years)** is where the harness is allowed to try
  candidate settings and pick the best one.
- **Era B (later years)** is touched exactly once, *after* the winner is
  chosen, to see how it does on weather it has never seen. That one number
  is the honest one.

If the era-B result disappoints, you do **not** nudge the candidate until
era B looks better — that would quietly turn era B into more era A. You run
the harness again with a different seed or a different rule structure, and
era B again gets one look at the new winner.

## The never-rerun-the-spent-holdout rule

The project's original final exam — all events from **2018 onward** — was
used exactly once, on 2026-08-19, by the single gated run recorded in
`detector/results_holdout/` (tamper-evident marker, hashes in
`detector/BACKTEST.md`). Those results stand forever; that data can never
again serve as an honest test, because we have already seen the answers.

The harness enforces this mechanically: any era that reaches into
2018-01-01 or later is refused with a `HoldoutAccessError`, and every data
read goes through `mining/data.py`, whose pre-registered guard refuses
holdout series at the loader level too. Both era A and era B therefore live
entirely in the pre-2018 development years.

## The versioned-config + SHA rule

The harness **never** writes `detector_config.json` or
`detector_config_tuned.json` — it refuses those filenames outright. Each
run produces:

- `runs/<tag>/detector_config_candidate_<tag>.json` — a **new** file with a
  `version: candidate-<tag>` field and a `retraining` provenance block
  (which ledger export, which eras, which seed, the base config's SHA-256);
- `runs/<tag>/detector_config_candidate_<tag>.json.sha256` — the
  candidate's own SHA-256 fingerprint;
- `runs/<tag>/retraining_report_<tag>.md` — the evidence: the ledger
  summary that motivated the run, the era-A search detail, and the single
  era-B result graded against the frozen bars.

The fingerprint is the candidate's identity. If a candidate is ever
adopted, its SHA-256 goes in the PR and in the docs, exactly as the current
config's hash is recorded — so what was reviewed is provably what ships.

## Known tuning artifacts (documented, not fixed)

- **flash_flood / `nbr_wet` can never fire.** In the frozen config
  (`detector/detector_config_tuned.json`, version `tuned-2026-08-19`, and its
  byte-identical shipped copy
  `weather/frappe/src/control/warnings_engine/detector_config.json`), the
  `nbr_wet` condition arms at `nbr_wet_frac >= 1.018` — but `nbr_wet_frac` is
  a fraction (wet neighborhood cells / valid cells, computed in
  `extraction/nbr_features.py` and `warnings_engine/features.py`) and is
  bounded by 1.0, so the condition is dead. The tuner's seeded random search
  simply landed above the feature's ceiling. It is **harmless**: `nbr_wet`
  sits in the any-of group `[nbr_rs6, nbr_max12, nbr_wet]`, so the group is
  satisfied by its other two members, and live behavior is exactly the
  behavior that was dev-tuned and holdout-graded. Surfaced by a live Hawaii
  run, 2026-08.
- Do **not** "fix" the threshold in place. The config is frozen — the engine
  verifies its SHA-256 at load, and the recorded scores belong to the file as
  it stands. Any correction, even to a provably dead condition, must arrive
  as a **new candidate config version** produced by this harness and
  revalidated on era B against the frozen bars, like any other rule change.

## Adoption = a human merging a PR

There is no other path to production. To adopt a candidate:

1. Open a PR that adds the candidate file (and its report) and updates the
   shipped config **as a reviewed diff**, with the candidate's SHA-256
   stated in the PR body.
2. Reviewers check the report: was the ledger volume sufficient, were the
   eras clean, is the era-B result genuinely better against the frozen
   bars, was the spent holdout untouched?
3. A human merges. Merge to main is what activates the change at the next
   compose — the harness itself has no write path to anything live.

## Running it

```
python3 retrain.py \
    --ledger ledger_export.json \
    --era-a 1996-01-01:2011-01-01 \
    --era-b 2011-01-01:2018-01-01
```

`--ledger` is an export of the Severe Weather Outcome table (JSON array or
CSV — the desk list view's export works). `--dry-run` runs the ledger gate
and every refusal check without touching series data. See the module
docstring in `retrain.py` for all flags. The harness reuses the existing
machinery rather than reimplementing it: `detector/tune.py` for the seeded
search and fold discipline, `detector/backtest.py` for the frozen metric
definitions, the combined feature construction from
`detector/run_backtest_holdout.py`, and the admin report endpoint's own
aggregation code for the ledger summary — so this folder cannot drift out
of agreement with the rest of the system.
