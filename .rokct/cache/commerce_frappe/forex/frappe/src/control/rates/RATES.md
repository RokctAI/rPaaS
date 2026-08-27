# The rates layer

Reference FX rates behind a swappable provider seam, cached once per pair
for every consumer. Control-plane code: this directory composes into
control-marked shells only; tenants reach it through the whitelisted proxy
in `src/tenant/rforex/api/rates.py`.

## Read this first: what these numbers are

The default provider serves **ECB reference rates via
[frankfurter.app](https://frankfurter.app)** — free, keyless, no account.
The ECB publishes **one reference rate per currency per business day**
(around 16:00 CET), explicitly for reference purposes. Consequences, worn
openly rather than papered over:

- `get_rate` returns the latest **daily** reference, not a live quote.
  `bid == ask == mid` because no spread exists to report, and `ts` carries
  the reference **date** (rendered as midnight UTC) because no quote time
  exists to carry.
- `get_history` rows have `open == high == low == close` — one rate per
  day is all the source publishes, and inventing an intraday range around
  it would be lying in candle form. Weekends and ECB holidays are absent,
  so a `days`-day window returns fewer than `days` rows.

This makes the layer suitable for **display and analysis**: conversions,
charts, market-state evaluation over daily closes. It is **not tick data
and not tradeable pricing**. Live broker bid/ask arrives later through the
broker connector seam (`api/account.py` `_broker_snapshot`), which is a
different seam on purpose — a chart may run on reference data; an order
may not.

Unavailable data raises `RatesUnavailable`. Per the house rule stated in
`api/account.py`: no fallback number is ever invented.

## The seam

```
provider.py     RatesProvider (abstract), pair validation, registry,
                get_rates_provider() — the config-driven factory
frankfurter.py  the default provider (ECB reference via frankfurter.app)
cache.py        the shared per-pair cache; THE public surface
```

Consumers import **only** the two cache accessors:

```python
get_cached_rate(pair)           # -> {"pair","bid","ask","mid","ts","source"}
get_cached_history(pair, days)  # -> [{"date","open","high","low","close"}, ...]
```

`pair` accepts `"EURUSD"` or `"EUR/USD"` (any case); the canonical form is
the 6-letter one, so every spelling shares one cache entry. Rate fetches
are shared across all consumers for `RATE_TTL_SECONDS` (900), history per
`(pair, days)` window for `HISTORY_TTL_SECONDS` (3600) — the same
one-evaluation-shared-by-everyone pattern as the weather module's grid
cells. Storage is `frappe.cache()` (Redis, cross-worker) on a composed
site, an in-process dict with identical TTL semantics without one (which
is what the frappe-free unit tests exercise).

## Config

| Key (site config) | Meaning | Default |
|---|---|---|
| `forex_rates_provider` | which registered provider serves rates | `"frankfurter"` |

Naming a provider that is not registered **raises** — a site asking for a
source it does not have should hear about it, not silently chart the
default's numbers.

## Adding a provider

1. Write `src/control/rates/<name>.py`: subclass `RatesProvider`,
   implement `get_rate` / `get_history` returning exactly the shapes above
   (`provider.RATE_KEYS` / `provider.HISTORY_KEYS`). If the source has a
   real spread, report real `bid`/`ask`; if not, `bid = ask = mid` — never
   a synthesized spread. State in the module docstring what the source
   actually is (reference vs tradeable, daily vs intraday).
2. Call `register_provider("<name>", <factory>)` at module import, and
   import the module where it will be seen (or extend the on-demand import
   in `get_rates_provider`).
3. Name it in site config: `"forex_rates_provider": "<name>"`.

No consumer changes: everything downstream reads the cache accessors.

## Pair validation

The strategy catalog pins no symbol list (`Forex Strategy Version` specs
carry a free-form `symbol`), so validation is structural ISO-4217: two
different three-letter alphabetic codes, `"EURUSD"` or `"EUR/USD"`.
Whether a pair actually EXISTS is the provider's answer — the default
source raises `RatesUnavailable` for pairs outside the ECB's ~30-currency
reference list.

## The tenant proxy

`src/tenant/rforex/api/rates.py` exposes `get_forex_rate` /
`get_forex_history` (whitelisted, declared in `manifest.json`). Because
`src/control/` is stripped from tenant-marked shells, the proxy reaches
this layer by guarded `frappe.get_attr` over the composed dotted path
(`{app_name}.rforex.control.rates.cache.…`) — the same dynamic-dispatch
pattern as the weather module's tenant proxy and orders'
`weather_notice.py`. Unlike weather's fail-silent garnish, an uncomposed
rates layer here raises a clear error: the rate is the payload, and an
empty answer that looks like a quiet market would be fabrication.
