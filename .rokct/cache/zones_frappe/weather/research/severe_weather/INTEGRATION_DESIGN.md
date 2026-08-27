# SDK integration design — severe-weather early warnings

Status: design doc only. No feature code ships with this document; it is the blueprint the
post-acceptance PRs (section 6) implement. Everything here is grounded in the current repos —
every load-bearing claim carries a `file:line` citation. Companion docs: `PLAN.md` (research
plan + frozen acceptance thresholds), `RECON_REPO.md` (repo recon), `RECON_DATA.md` (data
recon). Nothing below is activated until the detector passes the frozen thresholds in
`PLAN.md` ("Acceptance thresholds", frozen 2026-08-19).

---

## 1. Findings from investigation

### 1.1 The "existing telemetry pipeline" for admin-facing diagnostics

**Plain answer: there is no dedicated, module-consumable telemetry pipeline in the SDK
patterns available to the zones repo.** What actually exists:

1. **`frappe.log_error(...)` → Frappe's built-in Error Log doctype.** This is the universal
   admin-facing error mechanism every zones module uses, weather included:
   - `weather/frappe/src/weather/get_weather/get_weather.py:56` (config missing) and `:84`
     (`frappe.log_error(frappe.get_traceback(), "Weather Proxy API Error")` on provider
     failure);
   - `weather/frappe/src/weather/set_weather_alias/set_weather_alias.py:69`
     (`"Weather Alias Proxy Error"`);
   - the sibling scheduled jobs do exactly the same from inside scheduler context:
     `delivery/frappe/src/providers/lifecycle.py:171`, `:198`, `:221`;
   - API-layer siblings: `delivery/frappe/src/api/parcel_option/parcel_option.py:41` etc.
   Entries land in the desk **Error Log** list, which tenant admins can open — that IS the
   admin diagnostic surface today. This is how `get_weather` reports provider failures.
2. **A `core/telemetry` frappe module exists on both target shells** — it is composed into
   rcore (`the-rokct-protocol/core/utils/frappe/composer/rcore.json:64-70`) and
   deliveryplatform (`composer/deliveryplatform.json:47-53`) from the `RokctAI/core` repo.
   It carries an `api_error_log` doctype and a wildcard doc-events trace-context injector
   (`composer/radio.json:42` comment: "its frappe side already has src/telemetry and an
   api_error_log doctype"; `compose_backend.py:229` comment re: the `*`-doctype injector).
   Its dart side is an **empty placeholder** (`radio.json:42`), and its source lives in the
   `RokctAI/core` repo, which is not part of this change-set's readable scope — so its
   internal API cannot be designed against from here, and coupling to it via a
   `{app_name}.telemetry...` import would add a hidden cross-module dependency of the kind
   `RECON_REPO.md` §(g)4 already flags as a smell.
3. **Client side**: the only "telemetry" is base_sdk's standard interceptor chain —
   TimingInterceptor (timing telemetry) + ADR-006 `x-trace-id` stamping — which weather's
   gateway calls already ride (`weather/dart/lib/src/common/infrastructure/services/weather_service.dart:41-47`).
   The backend endpoints read (and discard) that header
   (`zones/frappe/src/api/delivery_zone/delivery_zone.py:33` shows the injected pattern).
4. **No Sentry, no push-to-admin notification pattern** exists anywhere in zones or in the
   protocol docs (searched: `sentry`, `telemetry`, `notify_admin`, `admin notification`).

**Design consequence (no invention):** admin diagnostics use `frappe.log_error` with stable,
grep-able titles (§4.3), exactly like `get_weather` does today, plus status fields on the new
doctypes so the desk list view doubles as a health dashboard. If Ray wants a richer pipeline,
the right home is the existing `core/telemetry` module in `RokctAI/core` — a follow-up
outside this change-set, not something to fake here.

### 1.2 Scheduled-job declaration and merge-alone activation

- Live precedent: `delivery/frappe/manifest.json:99-106` declares
  `hooks.scheduler_events.hourly` / `.daily` with `{app_name}`-tokenized dotted paths;
  implementations at `delivery/frappe/src/providers/lifecycle.py:145` and `:176`.
- The composer's `merge_hooks()` (`the-rokct-protocol/core/utils/frappe/compose_backend.py:901+`)
  merges `scheduler_events` (incl. a `"cron"` bucket keyed by croniter expressions,
  `compose_backend.py:933-973`); every dotted value must match
  `^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$` and cron keys
  `^[\w*/,\- ]+$` (`compose_backend.py:233-240`).
- **What guarantees activation by merge alone:** the weather module is already an enabled
  entry (`ref: main`) in BOTH frappe composer templates — rcore
  (`composer/rcore.json`, weather entry directly after telemetry/productivity) and
  deliveryplatform (`composer/deliveryplatform.json:54-61`). A merged addition *inside* the
  existing module (new `src/` files + new manifest hook entries) is picked up at the shells'
  next compose with zero template edits and zero manual steps. Pip deps ride the manifest's
  `dependencies` array, appended to the shell's requirements
  (`frappe_sdk_management.md:64-66`, `:164`; live precedent
  `zones/frappe/manifest.json:25-27` → `"staticmap"`).
- **Corollary:** the job runs on BOTH shell products for every site — it must be idempotent
  and cheap (also `RECON_REPO.md` §(g)6).

### 1.3 How the Dart half surfaces weather UI today

All UI lives in `weather/dart/lib/src/common/presentation/widgets/` and is exported through
the barrel `weather/dart/lib/weather_sdk.dart:49-60`. Entry points:

- `WeatherWidget` (adaptive header widget, `weather_widget.dart:53`) — embedded by shells via
  the manifest's zero-arg `embedded_widgets` seam `weatherHeaderWidget`
  (`weather/dart/manifest.json:14-23`) and the installed host template
  `templates/components/weather/weather_widget.dart` (→
  `lib/presentation/components/weather/weather_widget.dart`, `manifest.json:4-9`).
- **The payload's `alerts.alert` list is already consumed in three places** (weatherapi.com
  shape — `WeatherState.alerts` getter at
  `lib/src/common/application/weather/weather_state.dart:79-81`, `hasSevereAlerts` at
  `:151-157`):
  1. `weather_status_text.dart:46-53` — the header cycles the first alert's `event` name in
     red every 3 s;
  2. `weather_summary.dart:140-152` — natural-language summary prepends
     `'⚠️ Heads up: ${alert['headline']} - ${alert['desc']}'`;
  3. `weather_forecast_dialog.dart:354, 439-441` — per-hour alert chips in the dialog.
  So a heads-up **line** already exists for anything delivered in the alerts shape; what does
  not exist is a standalone **banner** widget or any attribution text.
- Placement that breaks no consumer: a **new, separately-exported widget**
  (`severe_weather_banner.dart`) that hosts opt into — plus, optionally, warnings mapped
  into the existing alerts shape (§2.4). Existing widgets are not modified except to append
  an attribution footer where warnings are rendered.
- **Attribution surfaces**: the banner itself, the `WeatherForecastDialog` alerts section,
  and the `WeatherInlineForecast` card when warnings are shown — all owned by this SDK, so
  the string can be rendered without touching any shell.

### 1.4 Where per-user/per-tenant locations come from

- The client resolves ONE location: the host wires
  `WeatherSdkConfig.locationResolver` to the logged-in shop/branch's stored coordinates
  (`weather/dart/templates/components/weather/weather_widget.dart:46-60`, pos main pattern
  `LocalStorage.getShopData()`), falling back to `DEMO_LATITUDE`/`DEMO_LONGITUDE`
  dart-defines (`weather_sdk_config.dart:92-101`).
- That lat/lng is reverse-geocoded client-side via GeoNames into `"city,cc"`
  (`weather_service.dart:108-149`) and **only the city string reaches the backend**:
  `{'location': cityLocation}` (`weather_service.dart:184-187`), consumed by
  `get_weather(location: str)` (`get_weather.py:35`). **The tenant backend never sees
  coordinates today** — the only server-side trace of interest is the ephemeral
  `weather_proxy_{location}` cache key (`get_weather.py:45`).
- Server-side location data that DOES exist on the composed shells: zones' `Delivery Zone`
  (per-shop polygon: `zones/frappe/doctype/delivery_zone/delivery_zone.json` fields
  `shop, delivery_fee, coordinates, address`; child rows
  `delivery_zone_coordinate.json` = `latitude, longitude`), delivery's `Delivery Point`
  (`delivery/frappe/doctype/delivery_point/delivery_point.json` fields incl.
  `latitude, longitude`) and `Provider Pickup Location`. These are shop/logistics locations,
  not a "where does this tenant want warnings" registry, and depending on them would couple
  weather to sibling modules.
- **Design consequence:** locations of interest must be made explicit — a small
  `Weather Watch Location` doctype **self-registered by client calls** (the new cmd's payload
  carries lat/lng, §2.2), with manual admin add/deactivate in desk as the escape hatch. No
  guessing from other modules' data.

### 1.5 Doctype/persistence patterns

- **The weather module declares no doctypes today** — `weather/frappe/` contains only
  `manifest.json` + two `src/` endpoints (verified by full listing). Persistence is
  `frappe.cache()` only (`get_weather.py:46, 79`).
- Siblings persist via module-root `doctype/<snake_name>/` trees:
  `delivery/frappe/doctype/` (20 doctypes), `zones/frappe/doctype/` (3),
  `map/frappe/doctype/driver_location`. Each dir = `__init__.py` + `<name>.json` +
  `<name>.py`; the JSON's `"module"` key is force-rewritten to the manifest name at compose
  (`frappe_sdk_management.md` — convention `"module": "{module_name}"`; e.g.
  `provider_pickup_location.json` still says `"module": "paas"` and composes fine).
- Doctypes are exported to shells via `hooks.fixtures` entries
  (`delivery/frappe/manifest.json`, `hooks.fixtures` — `{"dt": "DocType", "filters":
  [["name", "=", "Parcel Order"]]}` pattern).
- Scheduled jobs read/write doctypes with plain `frappe.get_doc`/`frappe.db.set_value`
  (`delivery/frappe/src/providers/lifecycle.py:80-138`).

---

## 2. Architecture

```
                     (hourly scheduler, both shells)
  s3://openmeteo  ──►  severe-weather evaluator  ──►  Severe Weather Warning docs
        or                 (per Weather Watch            + per-location status fields
  Open-Meteo API            Location; detector           (admin desk = health view)
  (config switch)           from PLAN.md §4)
                                                              │
  Flutter host ──POST /api/v1/method/rokct.platform.api──►    ▼
  (shop lat/lng)   {"cmd":"tenant.api.get_weather_warnings",  cmd handler: reads active
                    "payload":{"latitude":..,"longitude":..}} warnings, upserts the
                                                              watch location, returns
                                                              friendly copy + attribution
```

### 2.1 Scheduled backend job — the evaluator

- **Manifest** (`weather/frappe/manifest.json`), additive:

  ```json
  "scheduler_events": {
    "hourly": [
      "{app_name}.weather.warnings.evaluator.evaluate_watch_locations"
    ],
    "daily": [
      "{app_name}.weather.warnings.evaluator.sweep_expired_warnings"
    ]
  }
  ```

  Source at `weather/frappe/src/warnings/evaluator.py` — composes to
  `{app}/weather/warnings/evaluator.py`, mirroring
  `delivery/frappe/src/providers/lifecycle.py` ↔ `manifest.json:99-106` exactly.
- **Cadence: hourly**, with an internal freshness short-circuit: the evaluator caches the
  data source's `data_end_time` (from the bucket's `static/meta.json`,
  `RECON_DATA.md` §A1) and skips locations already evaluated against the same data horizon.
  ERA5 year/chunk files update daily (`update_interval_seconds: 86400`), so most hourly
  ticks are no-ops that cost one small meta read — cheap enough for the dual-shell
  composition (§1.2), while hourly keeps latency low for the faster-updating
  model-analysis archives (§3) and for newly registered locations.
- **Per tick**: for each active `Weather Watch Location` (stale ones — no client request in
  30 days — are skipped and eventually deactivated by the daily sweep): pull the detector's
  rolling feature window (per `PLAN.md` §4: a short window of recent hourly data plus the
  longer antecedent accumulations the flood classes need), run the per-class detectors, and
  upsert `Severe Weather Warning` docs. Idempotency: warnings are keyed
  (location, event_class, onset-window); re-evaluation updates in place, never duplicates.
  All work wrapped per-location in try/except so one bad location cannot starve the rest
  (same containment style as `lifecycle.py:171, 198, 221`).

### 2.2 Storage — two new doctypes (module-root `doctype/`, per §1.5)

1. **`Weather Watch Location`** — `latitude`, `longitude` (rounded to the 0.25° ERA5 grid
   per `PLAN.md` §1 join discipline; the rounded pair is the unique key), `label`
   (reverse-geocoded city string when known), `active`, `last_requested_at`,
   `last_evaluated_at`, `last_error` (small text), `consecutive_failures` (int).
   Upserted by every `get_weather_warnings` call; admins can create/deactivate rows in desk.
   Grid-rounding collapses all shops in a ~25 km cell into one evaluation — cost scales with
   distinct cells, not shops.
2. **`Severe Weather Warning`** — link to watch location, `event_class`
   (flash_flood | flood | destructive_wind | tornado_conditions), `severity`
   (heads_up | warning), `headline`, `message` (the friendly copy, rendered server-side so
   every client shows identical text), `onset`, `valid_until`, `issued_at`, `status`
   (active | expired | withdrawn), `precursors` (JSON text — which detector features fired;
   admin/debug only, never sent to clients).

Both declared as manifest `hooks.fixtures` DocType entries (delivery pattern, §1.5), JSON
`"module": "{module_name}"`. The client-facing cmd additionally caches its response via
`frappe.cache()` (`weather_proxy_*` pattern, `get_weather.py:45-49`) with a 600 s TTL.

### 2.3 Client-facing cmd

Follows the exact `{app_name}.tenant.api.*` aliasing `get_weather` uses
(`weather/frappe/manifest.json:5-9`):

```json
"whitelisted_methods": {
  "{app_name}.tenant.api.get_weather_warnings":
    "{app_name}.weather.weather.get_weather_warnings.get_weather_warnings"
}
```

- Source: `weather/frappe/src/weather/get_weather_warnings/get_weather_warnings.py`,
  function **decorated `@frappe.whitelist()`** (see §5.5 for the pre-existing gap on the two
  current endpoints).
- Client POSTs the universal gateway `/api/v1/method/rokct.platform.api` with
  `{"cmd": "tenant.api.get_weather_warnings", "payload": {"latitude": .., "longitude": ..}}`
  (`weather_service.dart:203-214` transport, `SDK_ECOSYSTEM.md:244-247`). Sending
  coordinates (not the GeoNames city string) removes the third-party geocode hop from the
  warnings path entirely and maps deterministically to the grid cell.
- Response (all fields server-rendered; clients do no meteorology):

  ```json
  {
    "warnings": [
      {
        "id": "SWW-2026-00123",
        "event_class": "flash_flood",
        "severity": "warning",
        "headline": "Flash flooding possible near Messina",
        "message": "Heavy rain could make water rise quickly ...",
        "onset": "2026-08-19T06:00:00Z",
        "valid_until": "2026-08-20T06:00:00Z",
        "issued_at": "2026-08-19T03:12:00Z"
      }
    ],
    "attribution": "Weather data by Open-Meteo.com",
    "generated_at": "2026-08-19T04:00:02Z"
  }
  ```

- **Failure contract:** internal errors (data source down, no evaluation yet, unknown
  location) return `{"warnings": [], "attribution": ...}` after `frappe.log_error` — they
  never `frappe.throw` to the client. The end-user surface for failure is *nothing* (§4.2).
  Auth failures still surface as normal HTTP errors from the gateway, like every cmd.

### 2.4 Dedicated cmd vs. piggybacking `warnings` into `get_weather` — evaluation

**Option A — dedicated `get_weather_warnings` cmd** (described above).

**Option B — additive `warnings` (or alerts-merge) field inside `get_weather`'s cached
payload.** Genuinely attractive because the UI already renders the weatherapi `alerts.alert`
shape in three widgets (§1.3): server-merging warnings as alert-shaped objects would light up
the existing header line, summary sentence, and dialog chips with zero dart changes. But:

1. `get_weather`'s payload is a **verbatim control-plane proxy** of a third-party feed
   (`get_weather.py:66-81`). Injecting locally computed warnings into it muddies provenance,
   risks colliding/duplicating with real weatherapi alerts for the same storm, and couples
   our copy to a schema we don't own.
2. `get_weather` is keyed by the GeoNames `"city,cc"` string (`get_weather.py:45`), while
   warnings are computed per lat/lng grid cell — the backend cannot reliably map city-string
   → watch location without a geocoding leg it doesn't have today (§1.4).
3. Cache lifetimes differ (10-min proxy cache vs hourly warnings), and a bug in the merge
   would degrade the *existing* weather surface — the one thing the safety rules say must
   not happen.

**Recommendation: Option A now.** Ship the dedicated cmd and the banner widget. Keep
Option B as an explicitly deferred phase-2 *additive* enhancement (a server-side merge of
active warnings into the `alerts.alert` array, guarded by a site-config flag, once a
city↔cell mapping exists via the watch-location `label` field) — it would then upgrade the
existing header/summary/dialog surfaces for free, still without any payload-shape break
(consumers already treat `alerts` as optional: `weather_state.dart:79-81` defaults `[]`).

### 2.5 Dart client surface

Additive files only, inside the structures the validator already checks
(`RECON_REPO.md` §(c): `application/`, `infrastructure/`, `di/` exists at
`lib/src/common/di/weather_sdk_di.dart`; only `base_sdk` imports per ADR-005):

- `infrastructure/services/weather_warnings_service.dart` — gateway POST of the new cmd,
  same transport/retry pattern as `weather_service.dart:197-253`; cmd string added as
  `WeatherSdkConfig.weatherWarningsCmd = 'tenant.api.get_weather_warnings'`
  (sibling of `weather_sdk_config.dart:70`).
- `application/warnings/` — `WeatherWarningsState` + notifier (riverpod, mirroring
  `weatherProvider`, `weather_service.dart:283-289`), refreshed on the same cadence as
  weather (`WeatherSdkConfig.refreshInterval`, `weather_sdk_config.dart:87`).
- `presentation/widgets/severe_weather_banner.dart` — the heads-up banner (§4.1); exported
  from the barrel (`weather_sdk.dart`) and offered as a second zero-arg
  `embedded_widgets` entry (`weatherWarningsBanner`) in `weather/dart/manifest.json` so
  shells embed it without importing weather_sdk (ADR-005 seam, `manifest.json:14-23`).
- Attribution footers added to `WeatherForecastDialog` / `WeatherInlineForecast` **only
  where warnings render** (§4.1) — no other change to existing widgets.

---

## 3. Data-source abstraction (production)

One tiny interface, two implementations, switched by tenant site config — mirroring how
`get_weather` reads `frappe.conf` (`get_weather.py:52-65`):

```python
class WarningsDataSource:            # weather/frappe/src/warnings/sources/base.py
    def hourly_series(self, lat, lon, variables, start_utc, end_utc): ...
    def data_horizon_utc(self): ...  # freshness short-circuit input (§2.1)
```

- **Default: `OpenMeteoS3Source`** — anonymous ranged reads from `s3://openmeteo` via
  `omfiles` + `s3fs`, exactly the access pattern proven in `RECON_DATA.md` §A2/A4
  (~11 GETs / ~15 kB per point-year-variable; nearby cells share chunks). Zero licensing
  cost, no API keys, no rate limits; ERA5 archive is daily-updated. Adds
  `"dependencies": ["omfiles", "s3fs"]` to `weather/frappe/manifest.json`
  (precedent: `zones/frappe/manifest.json:25-27`; composer appends to shell requirements,
  `frappe_sdk_management.md:164`).
  - **Known limitation to design around:** the ERA5 archive lags real time by ~2–7 days
    (`data_end_time` 2026-08-13 observed on 2026-08-19, `RECON_DATA.md` §A1). Antecedent
    features (soil moisture, multi-day rain accumulation) come from ERA5; the *recent-hours*
    part of the feature window must come from the same bucket's near-real-time
    model-analysis archives (`ecmwf_ifs_analysis_long_window`, `ncep_gfs025` rolling chunks
    — same `.om` format, same reader). Whether the detector's ERA5-trained features transfer
    cleanly to those analysis fields is an open validation item for the backtest (§7).
- **Config-switchable: `OpenMeteoApiSource`** — the commercial Open-Meteo API (if Ray buys a
  plan): plain HTTPS+JSON via `frappe.make_get_request` (the `get_weather.py:74` pattern), no
  extra pip deps, no data lag concerns, SLA'd. Site config:

  ```
  "severe_weather_source": "openmeteo_s3" (default) | "openmeteo_api",
  "openmeteo_api_key": "..."             (required only for openmeteo_api)
  ```

  Unknown keys → default source; missing/invalid API key → log + fall back to S3, never a
  user-visible failure.
- **Attribution is unconditional**: Open-Meteo data is CC-BY-4.0
  (`RECON_DATA.md` §A4) — the literal string **"Weather data by Open-Meteo.com"** is carried
  in every cmd response (§2.3) and rendered on every surface that displays a warning (§4.1),
  regardless of which source produced it.

---

## 4. End-user surface, copy, and admin telemetry

### 4.1 End-user surface

`SevereWeatherBanner`: a slim, dismissible-per-day card (host places it; header slot or top
of body flow), showing at most the single most severe active warning: headline + message +
attribution footer in small muted type: *Weather data by Open-Meteo.com*. Tapping expands
remaining warnings. Colors stay calm — the existing palette's warning tones
(`presentation/theme/weather_colors.dart`), never flashing/red-alert styling for
`heads_up` severity.

**Copy principles:** calm, human, concrete about what to *do*, no probabilities, no
meteorology jargon (no "POD", "convective", "mesocyclone", no percentages). Place name = the
watch location's `label` (falls back to "your area"). Exact server-side copy per class and
severity ("heads_up" = early notice; "warning" = act now):

| Class | `heads_up` | `warning` |
|---|---|---|
| Flash flood | "Heavy rain could cause fast-rising water around {place} in the next day or so. If you're near streams or low-lying roads, keep an eye out." | "Flash flooding looks likely around {place} in the coming hours. Please avoid low bridges and flooded roads — even shallow moving water is dangerous." |
| Flood | "Rivers and low ground around {place} are getting very wet. Flooding is possible over the next few days." | "Flooding is expected around {place} in the next day or two. If stock or vehicles sit on low ground, now is a good time to move them up." |
| Destructive wind | "It may get very windy around {place} tomorrow. Worth tying down anything loose outside." | "Damaging winds are expected around {place} within the next day. Secure loose items, park clear of trees, and be ready for possible power cuts." |
| Tornado conditions | "Conditions around {place} could turn stormy and severe today. Keep an ear on local alerts." | "Dangerous storm conditions are building around {place}. If a storm hits, head into a sturdy building and stay away from windows." |

Headlines follow the same voice: "Flash flooding possible near {place}", "Very windy day
ahead near {place}", etc. (The "⚠️ Heads up:" framing matches the tone the suite already
uses at `weather_summary.dart:149`.)

**What "nothing" looks like on failure:** nothing. No active warnings, cmd failure, empty
response, or source outage all render `SizedBox.shrink()` — no banner, no error text, no
retry chip, zero layout shift. This is a deliberate contrast with the core weather widget,
which *does* show retry affordances ("Failed to fetch weather - Tap to retry",
`weather_widget.dart:392-394`): weather is a feature users asked to see; a warning that
can't be computed must not manufacture anxiety or UI noise. Failures are an admin concern
(§4.2), never an end-user one.

### 4.2 Admin telemetry — exactly what goes where (per finding §1.1)

No new pipeline is invented. Everything admin-facing uses the two mechanisms that exist:

| Event | Mechanism | Where the admin sees it |
|---|---|---|
| Evaluator failure for a location | `frappe.log_error(frappe.get_traceback(), "Severe Weather Evaluator Error")` — logged on first failure and then at most once per location per 6 h (Error Log spam guard; the job runs hourly on two shells) | desk **Error Log** list (same place as today's "Weather Proxy API Error", `get_weather.py:84`) |
| Data-source failure (S3/API unreachable, bad key, stale horizon > 48 h) | `frappe.log_error(..., "Severe Weather Data Source Error")`, same rate-limit | desk Error Log |
| cmd handler internal failure | `frappe.log_error(..., "Severe Weather Warnings API Error")`; client still gets `{"warnings": []}` | desk Error Log |
| Per-location health | `last_evaluated_at`, `last_error`, `consecutive_failures` fields updated by the evaluator on the **Weather Watch Location** doc | desk list view of Weather Watch Location = health dashboard (sortable by `consecutive_failures`) |
| Request tracing | nothing new — gateway calls already carry `x-trace-id` via base_sdk's interceptor chain (`weather_service.dart:41-47`) | existing ADR-006 flow |

Stable titles are load-bearing: they are the grep keys admins/support use in Error Log.
If Ray later wants structured telemetry (counters, dashboards), the follow-up is the
existing `core/telemetry` module in `RokctAI/core` (§1.1.2) — out of scope here.

---

## 5. Backward compatibility & safety

1. **No changes to existing cmd payload shapes.** `get_weather` and `set_weather_alias`
   byte-identical. The only touched existing surface is additive UI (attribution footer
   where warnings render). The deferred alerts-merge (§2.4 Option B) is additive too and
   ships only behind a site-config flag, later.
2. **No deletion, anywhere.** New files + additive manifest keys only. Shells compose at
   `ref: main` (`SDK_ECOSYSTEM.md:337`) — a breaking merge silently breaks every consumer at
   next compose, so every PR in §6 must leave a mid-sequence compose fully working.
3. **Versioning:** `weather/dart/manifest.json` version `1.2.1` → `1.3.0` **in the same
   commit** as the dart surface (SDK_ECOSYSTEM.md rule, `RECON_REPO.md` §(e)), and that same
   commit **creates the missing `weather/dart/CHANGELOG.md`** (gap: only delivery and map
   have one) with entries for 1.2.x history as far as reconstructible plus the 1.3.0 entry.
   The version bump is also the propagation trigger — the sdk-bump-poller
   (`shared-workflows/.github/workflows/sdk-bump-poller.yml`) diffs `*/dart/manifest.json`
   and dispatches dependent shell builds; no manual hookups. The frappe manifest has no
   version field; backend activation is compose-driven (§1.2). Leave the known
   pubspec-vs-manifest skew alone (manifest is authoritative, `SDK_ECOSYSTEM.md:48-50`).
4. **Token rules:** exactly two tokens exist — `{app_name}` and `{module_name}`
   (`frappe_sdk_management.md`; `RECON_REPO.md` §(b)). Cross-module imports (none planned —
   new backend files import only frappe + stdlib + the pinned deps, NOT the
   `{app_name}.comms`/`{app_name}.core.helpers` star-imports the legacy files carry) would
   use `{app_name}.`; doctype JSONs use `"module": "{module_name}"`; scheduler/whitelist
   values are `{app_name}`-tokenized pure dotted paths (compose-time regex,
   `compose_backend.py:233-240`). Leftover tokens after compose are lint failures under
   `ROKCT_COMPOSE_STRICT=1`.
5. **`@frappe.whitelist()`:** both existing weather endpoints **lack the decorator**
   (`get_weather.py:35`, `set_weather_alias.py:35`) while every sibling module decorates its
   API functions (`map/frappe/src/api/driver_order/driver_order.py:130`,
   `delivery/frappe/src/api/delivery/delivery.py:50`). **Flagged for Ray here and in the PR —
   not fixed silently** (it either means the two cmds are broken behind the gateway's
   `is_whitelisted()` check, or a shell-side mechanism outside this repo whitelists them;
   changing them without knowing which is a behavior change). Every NEW endpoint in this
   design carries `@frappe.whitelist()`.
6. **`sdk_validator --compliance` implications for the new dart surface**
   (`shared-workflows/scripts/sdk_validator.py`, rules per `RECON_REPO.md` §(c)):
   - all new files land in already-valid structures: `application/<feature>/` (new
     `warnings/` subfolder satisfies the feature-subfolder rule, lines 271-284),
     `infrastructure/services/` (unchecked minority pattern — fine),
     `presentation/widgets/`, existing `di/` (its absence would be an ERROR, lines 321-322
     — it exists);
   - **no `infrastructure/models/` is introduced** — if response models are ever added they
     MUST use the `models/data/` + `models/response/` slices (missing slice = ERROR, lines
     291-301) and plural `repositories` (lines 307-310);
   - imports stay `base_sdk`-only (ADR-005 check, lines 350-412) and any new
     manifest-referenced template paths must resolve (import validation, lines 594-610);
   - the compliance scanner runs over `dart/` with error-severity findings blocking; new
     files follow the existing files' conventions (which currently pass).
7. **Job safety:** evaluator idempotent, per-location error containment, grid-cell
   dedup, freshness short-circuit — because it runs hourly on BOTH rcore and
   deliveryplatform for every site (§1.2).

---

## 6. Rollout plan — numbered PR sequence

Ground rule for every PR: merging it must be the ONLY activation step (compose templates
already reference `weather/frappe` and the flutter templates already carry `weather_sdk`;
the bump-poller handles client propagation). No manual steps, ever.

1. **PR #35 (this branch — research + this design).** Research-only; invisible to composer
   and validator (composer references `weather/frappe`/`weather/dart` by explicit path;
   validator only discovers `dart/manifest.json`). **Stays draft** until Ray has reviewed
   the design; merging activates nothing.
2. **PR 2 — detector + backtest (research only).** Detector implementation, backtest
   harness, and results vs. the frozen thresholds under
   `weather/research/severe_weather/`. **Stays draft until the held-out backtest meets ALL
   frozen thresholds** (`PLAN.md`, frozen section) — this PR is the acceptance gate for
   everything below. Also validates the ERA5→near-real-time-archive feature transfer (§3).
3. **PR 3 — backend integration (first activating PR).** Contains, in one merge:
   `doctype/weather_watch_location/` + `doctype/severe_weather_warning/`;
   `src/warnings/` (evaluator, detector port, `sources/` with both impls);
   `src/weather/get_weather_warnings/` (decorated `@frappe.whitelist()`);
   manifest additions — new `whitelisted_methods` alias, `scheduler_events`
   (hourly + daily sweep), `fixtures` for both doctypes, `dependencies`
   (`omfiles`, `s3fs`); backend tests (delivery's `tests/` mock pattern,
   e.g. `delivery/frappe/tests/test_intercity_providers.py:73`). Merge → next shell compose
   runs migrations (fixtures), installs deps, registers cmd + jobs. Draft until PR 2 is
   accepted and merged. Safe alone: no client calls the cmd yet; the evaluator simply finds
   zero watch locations until clients arrive.
4. **PR 4 — dart client surface.** Warnings service + state/notifier + `SevereWeatherBanner`
   + attribution footers + barrel exports + `embedded_widgets` entry + config cmd constant;
   `manifest.json` `1.3.0` bump **and `CHANGELOG.md` creation in the same commit**. Merges
   only after PR 3 is on main (server-first ordering; even so, the client's failure contract
   renders nothing if a stale shell lacks the cmd). Merge → bump-poller dispatches dependent
   shell builds within ~10 min. Draft until PR 3 merges.
5. **PR 5 (optional, later) — `get_weather` alerts-merge (Option B, §2.4)** behind a
   site-config flag, upgrading the existing header/summary/dialog surfaces. Needs the
   city↔cell mapping; separate decision with Ray after the banner has field mileage.

Each activating PR (3, 4) must state in its body: what composes where, the §5 safety
checklist, and the whitelist-gap flag (§5.5) so it is re-surfaced to Ray at every step.

---

## 7. Open questions / risks for Ray

1. **The `@frappe.whitelist()` gap** on both existing weather endpoints (§5.5): are those
   cmds currently working in production? The answer determines whether a separate fix PR is
   needed (and proves/disproves a shell-side whitelisting mechanism we can't see from zones).
2. **ERA5 real-time lag** (§3): default S3 sourcing needs the near-real-time model-analysis
   archives for the recent-hours features; if backtest transfer validation (PR 2) shows the
   features don't transfer, the commercial API (or a control-plane feed) becomes the default
   for the live path — a licensing/cost decision for Ray.
3. **`omfiles` on shell servers**: Rust-backed wheel; needs a compatible wheel for the
   shells' Python/platform at compose-time `pip install`. If any shell platform lacks a
   wheel, the API source becomes the default there.
4. **Warning push vs. pull**: this design is pull-only (banner refresh). Real push (FCM)
   would touch `boot_hooks`/`di_hooks` ownership rules (`SDK_ECOSYSTEM.md` invariants,
   `RECON_REPO.md` §(d)6) and is a separate decision.
5. **Copy sign-off**: the §4.1 strings ship server-side (single source of truth) — Ray
   should approve the exact wording before PR 3; changing copy later is a backend-only
   deploy, no client release.
6. **Tenant privacy note**: watch locations are shop coordinates already stored by the
   platform, rounded to a ~25 km grid — no end-user/customer locations are collected.
