# Market state

Per-pair market context, computed **control-side once per pair** and shared by
every tenant that asks — the weather module's grid-cell serving pattern applied
to currency pairs. Tenants call the whitelisted proxy
(`{app_name}.api.forex.market_state`, `src/tenant/rforex/api/market_state.py`);
the proxy resolves the control engine and returns its dict verbatim.

**Everything here is descriptive, not predictive.** The engine reports which
session windows contain a timestamp, how wide yesterday's daily range was
relative to its own recent average, and how old the cached rate is. It contains
no forecast, no signal, no recommendation, and adding one would be a different
module with a different review bar.

## The dict, field by field

`get_market_state(pair, ts=None)` returns:

| Field | Meaning |
|---|---|
| `pair` | The pair asked about, normalised to upper case (`EURUSD`). |
| `ts` | The ISO-8601 UTC instant that was judged. |
| `market_open` | `false` exactly on `[Friday 22:00, Sunday 22:00)` UTC, `true` the rest of the week. Spot forex trades continuously through weekdays. |
| `sessions.active` | Which of `sydney` / `tokyo` / `london` / `new_york` windows contain `ts`. **Always `[]` when the market is closed** — the raw Sydney window covers early Saturday UTC, and reporting it as trading would be fabricated liveliness. |
| `sessions.overlaps` | `{"tokyo_london": bool, "london_new_york": bool}` — the two overlaps traders size positions around. Both `false` whenever the market is closed. |
| `volatility` | See below. |
| `rate` | The rates layer's cached rate dict (`pair`, `bid`, `ask`, `mid`, `ts`, `source`), **verbatim**, or `null` when the layer has nothing. Never synthesised here. |
| `rate_staleness.age_seconds` | Age of `rate.ts` at evaluation time; `null` when there is no rate or its timestamp cannot be parsed. |
| `rate_staleness.threshold_seconds` | The constant below, echoed so clients need not hardcode it. |
| `rate_staleness.stale` | `age_seconds > threshold`, or `true` whenever the age is unknowable — a rate that cannot prove its freshness is not presumed fresh. |
| `rate_staleness.reason` | `null` on a normal read; otherwise `no_cached_rate`, `rates_layer_unavailable`, or `unparseable_rate_ts`. |
| `computed_at` | ISO-8601 UTC of the evaluation. Within a TTL window every caller sees the same `computed_at` — that is the shared-evaluation pattern working, not a bug. |

## Session boundaries (the exact choices)

Fixed **UTC** windows, half-open `[open, close)` — the opening minute is in,
the closing minute is out:

| Session | UTC window |
|---|---|
| Sydney | 22:00 – 07:00 (wraps midnight) |
| Tokyo | 00:00 – 09:00 |
| London | 08:00 – 17:00 |
| New York | 13:00 – 22:00 |
| **Weekend closure** | **Friday 22:00 → Sunday 22:00** |

These are **approximations by design**:

- **DST is deliberately ignored.** These are the common textbook fixed-UTC
  windows, not the drifting local hours of each financial centre. Real edges
  move by an hour twice a year, in opposite directions per hemisphere; there is
  no bell that rings when "the London session" starts, so we chose stable and
  reproducible over pseudo-precise.
- The weekend edges vary by broker (roughly 21:00–22:00 UTC both ends, shifting
  with US DST). 22:00 was chosen for both because it coincides with this
  model's New York close and Sydney open, so the weekly calendar has no gap and
  no overlap at its seams.

The chosen windows tile the weekday clock completely: at every open-market
instant at least one session is active.

## Volatility (descriptive buckets, not predictions)

Input is the rates layer's daily history — **daily ECB reference data**, one
official fix per day, not tick data. A "daily range" here is `high - low` of
those reference values and is systematically **narrower than the true intraday
range**. The measures are comparable with each other, which is all a bucket
needs; the absolute numbers must never be quoted as intraday ranges.

- `average_daily_range` — mean range over the **baseline**: every usable candle
  except the most recent (including it would drag the average toward the value
  being judged).
- `latest_daily_range` — the most recent candle's range.
- `ratio` — `latest / average`.
- `state` — from module constants in `volatility.py`:
  - `quiet` when `ratio < 0.7` (`QUIET_BELOW`)
  - `elevated` when `ratio >= 1.3` (`ELEVATED_AT`)
  - `normal` in between
  - `unknown` when fewer than `MIN_BASELINE_DAYS = 3` usable baseline candles
    exist, or the baseline is degenerate (flat zero). Never a made-up
    `normal`.

The thresholds are round conventions — where a human eyeball starts calling a
chart quiet or busy — not fitted parameters. `basis: "daily_reference"` rides
in the block as the honesty marker, and `sample_size` says how many usable
candles the verdict saw.

**"Elevated" is a statement about yesterday.** It carries no implication about
tomorrow.

## Staleness threshold

`RATE_STALE_AFTER_SECONDS = 36 * 3600` (36 hours): the daily ECB cadence — one
fix per business day, published mid-afternoon CET — plus half a day of slack.

The flag is **mechanical by design**: over a weekend Friday's fix ages past 36
hours and is flagged stale, because it genuinely is that old. Read `stale`
together with `market_open`; a stale rate on a closed market is expected and
truthful for daily reference data.

## Caching and freshness of the verdict itself

- `frappe.cache()` (Redis) with `CACHE_TTL_SECONDS = 60` when frappe is
  available; an in-process dict with the same TTL otherwise (the unit-test
  environment).
- An explicit `ts` argument **bypasses the cache in both directions** — a
  historical instant is a question, not the shared present, and caching it
  would poison everyone else's answer. The tenant proxy therefore exposes no
  `ts` parameter at all.

## Failure honesty

- Rates-layer **exceptions propagate untouched** (unknown pair, no data): the
  caller sees the rates layer's own refusal, not a half-filled state dict.
- Rates layer **absent or empty**: `rate: null` plus a named
  `rate_staleness.reason`, while the session verdict — which needs no market
  data — stays fully populated.
- The tenant proxy **throws** when no engine composes into the shell. Market
  state is the payload, and an empty-but-200 response would read as "no
  sessions active, no volatility" — fabricated market data, which this SDK
  refuses everywhere.
