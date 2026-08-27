# BACKTEST.md — frozen protocol for the London Breakout bot

Written **before** any backtest has run. No backtest has run: everything
below is blocked on the tick-data export (step 1), which only Ray can do.
Results, when they exist, are reported against this file as written —
misses included, no post-hoc threshold moves. If a number below turns out
to be a bad choice, that is a finding to report, not a line to edit.

The parameters being tested are a **checksummed, immutable spec** — a
`Forex Strategy Version` row. A backtest grades one checksum. Any change
that comes out of tuning ships as a **new version** with a new checksum
(`outcomes/frozen.py` refuses mutation with `FrozenConfigError`); nothing
retunes in place.

## 1. Data requirement (blocked on Ray)

- **What:** tick data for the traded symbol (GBPUSD, per the strategy
  spec), exported from **cTrader Desktop** — the tick archive the platform
  downloads for tick-data backtesting. This export is a manual step only
  Ray can perform against his broker account.
- **Format:** the CSV cTrader Desktop produces — one row per tick: UTC
  timestamp with millisecond precision, bid, ask.
- **How much:** enough history to give both eras below at least 12 months
  each; more is better. The export's exact first/last timestamps are
  recorded here in a dated amendment **before** the first run.

Bid *and* ask matter: expectancy is measured **after spread**, and the
spread comes from the data, not from an assumption.

## 2. Era split (fixed at data delivery, before any run)

When the export lands, it is split chronologically and the boundary
timestamp is committed here before anything reads the data:

- **Tune era** — the earliest ~70% of the export. Search, fit, iterate
  freely.
- **Holdout era** — the most recent ~30% (minimum 12 months). Read
  **once**, blind, after the candidate spec is final.

`outcomes/frozen.py`'s `BacktestEraGuard` enforces this in code: any
tuning-time read of holdout data raises `HoldoutAccessError`, and the
holdout evaluation can be started exactly once — a second attempt raises,
forever, because a holdout whose answers have been seen proves nothing. If
the holdout result disappoints, the candidate failed. The remedy is a new
candidate and, when enough new time has passed, a new holdout era going
forward — never a second look at the spent one.

## 3. Pre-stated metrics and bars (frozen)

Measured on the holdout era only. Every emitted signal counts, including
signals that expired untriggered — the denominator is never curated.

| Metric | Definition | Bar |
|---|---|---|
| Hit rate | wins / all settled signals (losses, scratches and expiries in the denominator) | ≥ 40% |
| Expectancy after spread | mean pips per settled signal, entry and exit priced at the touched side of the book (buy at ask, sell at bid) | > 0 pips |
| Max drawdown | largest peak-to-trough fall of the cumulative R-multiple curve, in R | ≤ 15 R |
| Sample size | settled signals in the era | ≥ 100, else **no verdict** |

Below the sample-size minimum the result is `insufficient data` — the same
rule the live outcome ledger applies (`outcomes/report.py`). A hit rate
over 30 trades is noise and will not be reported as if it were signal.

## 4. Reporting commitment

- The report states every metric above, computed exactly as defined,
  side by side with these bars — pass or fail, no reweighting, no
  "excluding the news week", no alternative denominators.
- The tested spec's checksum, the era boundaries, and the export's
  first/last timestamps appear in the report.
- A failed backtest is published the same way as a passed one.
- Adoption of any tuned candidate = a reviewed PR publishing a **new**
  `Forex Strategy Version`, which users opt into. No other path exists.
