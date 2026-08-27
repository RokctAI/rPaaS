## 1.5.0

* Offline caching for the severe-weather feed (disaster-management wave;
  the banner keeps working through dead spots exactly when hazards make
  connectivity least reliable):
  * New `WeatherWarningsCache`: the last successful warnings payload is
    persisted per watch location (2-decimal lat/lng key) as a JSON document
    in base_sdk's shared drift database - the `AppDatabase` generic KV
    store, same pattern as base's `CustomerCartStore`, so no dedicated
    drift table and no new pub dependency (ADR-005: the SDK still imports
    base_sdk only).
  * `WeatherWarningsService.getWarnings` now falls back to that cache on
    no connectivity or a failed fetch, serving only notices still inside
    their validity window (expired notices - and notices without a
    `valid_until` bound, which could otherwise show stale forever - are
    never rendered from cache). A successful refresh reconciles the cache:
    active notices overwrite it, a genuinely empty response invalidates it.
  * Cache-served notices are flagged on the state
    (`WeatherWarningsState.fromCache`/`cachedAt`) and the banner adds a
    subtle freshness marker ("As of 14:30") in the same muted style as the
    attribution line; the label routes through base_sdk's translation
    layer (new manifest `tr_keys` entry `asOf` -> `as.of`).
  * Strictly fail-closed: every cache read/write/parse error is swallowed
    and degrades to the exact pre-cache behavior (empty state, no banner,
    no error UI). `SevereWeatherWarning` gains `toJson()`/`isActiveAt()`
    for the round-trip.
* Seen/opened delivery receipts (app half of acknowledgment tracking; the
  `{app_name}.tenant.api.ack_weather_notice` endpoint ships separately and
  this release is safe in any merge order with it):
  * New `WeatherNoticeAckService`: when the banner renders a notice it
    fire-and-forgets `{"cmd": "tenant.api.ack_weather_notice", "payload":
    {"warning_id": ..., "event": "seen", "client_ts": <ISO-8601>}}` through
    the universal platform gateway; tapping to expand sends the same with
    `"opened"`. Cmd string on `WeatherSdkConfig.weatherNoticeAckCmd`.
  * Exactly one attempt per warning per event per app session (in-session
    de-dupe, no retries), silent on every failure, and never blocks or
    slows the UI - on backends without the endpoint the receipts simply
    vanish and nothing changes.
* Purely additive: cmds, payload shapes and every existing surface are
  unchanged; with an unavailable cache and no ack endpoint the banner
  behaves byte-identically to 1.4.0.

## 1.4.0

* Driver-host wiring for the severe-weather banner (courier home surface;
  the banner widget itself shipped in 1.3.0/1.3.1 and is unchanged):
  * New `app_type.driver` manifest block. Its install lays a courier-aware
    variant of the host wiring template over the same destination as the
    generic one (`lib/presentation/components/weather/weather_widget.dart`;
    flavor installs sync after top-level ones, so driver composes
    deterministically get the courier file while every other host keeps
    the generic shop-location template, and the installer's hash guard
    still preserves host edits).
  * The driver template's `configureWeatherSdk()` wires
    `WeatherSdkConfig.locationResolver` to the courier's live position in
    base_sdk's selected-address slot - the slot delivery_sdk's
    `CourierStorage.saveSelectedLocation` persists the courier map
    position through (ADR-005: the template imports base_sdk only). No
    stored position falls back to the DEMO_LATITUDE/DEMO_LONGITUDE
    dart-defines, exactly like the generic template.
  * New driver `boot_hooks` entry runs `configureWeatherSdk()` at startup:
    driver shells embed no weather header widget (whose build is what
    lazily configures the SDK on pos/manager), so without the hook nothing
    would set the resolver before the banner's first warnings fetch.
  * Purely additive: the generic template, both embedded_widgets seams and
    all existing hosts' behavior are unchanged; driver compositions that
    do not include weather_sdk are unaffected.

## 1.3.1

* Severe-weather feed: new soft "advisory" severity tier (backend
  neighbor-propagation notices - conditions nearby may reach this area).
  * `SevereWeatherWarning` gains `isAdvisory` and `severityRank`; "most
    urgent first" ordering is now advisory < heads_up < warning (unknown
    future tiers rank with heads_up, so a notice is never dropped or
    hidden by an unrecognized severity value).
  * `SevereWeatherBanner`: when every active notice is advisory-tier, the
    card renders its most muted form - slightly smaller, quieter type and
    tighter padding than the heads-up presentation, same server-authored
    calm copy and same severity-independent colors, with the mandatory
    Open-Meteo attribution still shown. With mixed severities the most
    urgent notice wins the collapsed line at the default presentation, as
    before.
  * Purely additive: payload shape, cmd, and all existing tiers'
    rendering are unchanged.

## 1.3.0

* Severe-weather heads-up surface (client half of the early-warning
  feature; the backend half ships separately and this release is safe in
  any merge order with it):
  * New `WeatherWarningsService` fetches active warnings for the shop's
    lat/lng through base_sdk's universal platform gateway
    (`{"cmd": "tenant.api.get_weather_warnings", "payload": {latitude,
    longitude}}` - raw coordinates, no geocode hop; cmd string on
    `WeatherSdkConfig.weatherWarningsCmd`). Explicit send/receive
    timeouts, retry with linear backoff, and a strict silent-failure
    contract: ANY failure (offline, HTTP error, malformed payload, or a
    composed backend that does not expose the cmd yet) resolves to the
    empty state - the service never throws to the UI.
  * New `application/warnings/` state layer: `SevereWeatherWarning` +
    `WeatherWarningsState` (server-rendered copy passed through verbatim;
    items missing user-visible text are dropped) and
    `WeatherWarningsNotifier`, refreshing on the suite's shared
    `WeatherSdkConfig.refreshInterval` cadence.
  * New `SevereWeatherBanner` widget: a slim, calm card showing the single
    most urgent active warning (headline + friendly message), tap to
    expand the rest, dismissible per day (a changed warning set reappears
    immediately). All end-user copy is server-authored heads-up wording -
    never sirens, emoji, jargon, probabilities, the word "warning", or
    color-coded severity levels (in South Africa only the national weather
    service may issue official severe-weather warnings; severity is
    expressed through wording intensity alone, over one muted,
    severity-independent accent). Renders
    `SizedBox.shrink()` when there is nothing to show, so it causes zero
    layout shift and no error/retry UI, ever. Carries the mandatory
    "Weather data by Open-Meteo.com" attribution (CC-BY-4.0) whenever
    warnings are displayed.
  * New zero-arg `embedded_widgets` seam `weatherWarningsBanner` so shells
    can embed the banner without importing weather_sdk directly
    (ADR-005).
  * Purely additive: no existing widget, cmd, or payload shape changed;
    existing surfaces are untouched and byte-compatible.

## 1.2.1 and earlier

* Pre-changelog history (this file starts at 1.3.0). The 1.2.x line is the
  refork port of pos main's JuvoONE weather suite - adaptive header widget,
  forecast dialog, popup-free inline forecast, extended forecast, rain
  feedback - wired through base_sdk's platform gateway and interceptor
  chain. Details in the repo history for `weather/dart/`.
