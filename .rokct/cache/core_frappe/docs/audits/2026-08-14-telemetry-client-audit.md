# TelemetryClient audit — 2026-08-14

**Scope:** `base/dart/lib/src/services/telemetry.dart` (`TelemetryClient`,
`TraceIdInterceptor`, `generateTraceId`), `base/dart/lib/src/services/timing_telemetry.dart`
(`TimingTelemetry`, `TimingInterceptor` — added by PR #34, merged 2026-08-13),
`base/dart/lib/src/handlers/http_service.dart`, `base/dart/lib/src/handlers/token_interceptor.dart`,
backend endpoint `telemetry/frappe/src/telemetry/log_frontend_error/log_frontend_error.py`,
and the Next.js mirror `base/nextjs/src/services/telemetry.ts`.

## Summary verdict

The client is deliberately minimal — fire-and-forget, no queue, no retry — and that
minimalism is mostly sound: nothing in the telemetry path blocks app code, and the
one caller of `logError` (`TimingTelemetry`) sends a JSON-safe payload. Two real
defects were found and fixed in this PR: `logError` could throw a serialization
error out of an unawaited future (breaking its own "never break the app" contract),
and request durations were measured with the wall clock instead of a monotonic
clock. The most serious remaining issue is not in `TelemetryClient` itself but next
to it: `HttpService` wires a `LogInterceptor` that prints the `Authorization` bearer
token and full request/response bodies to device logs in **release** builds. That,
plus several structural gaps (no offline persistence, unbounded per-window path
cardinality, timing reports landing in the backend *error* pipeline), are documented
below as recommendations, not changed here.

## Findings by severity

### High

- **H1 — `logError` could throw out of an unawaited future** *(fixed)*.
  `telemetry.dart` (pre-fix line 67): `debugPrint('==> telemetry ${jsonEncode(payload)}')`
  ran **before** the `try` block. Any non-JSON-encodable value in `context`
  (`DateTime`, `Duration`, an arbitrary object) threw `JsonUnsupportedObjectError`
  out of `logError`. The only current caller (`timing_telemetry.dart:129`)
  fire-and-forgets the returned future, so the throw surfaced as an unhandled
  async error — the exact failure the class documents as impossible
  ("telemetry must never break the app"). PR #34's own payload is all
  strings/ints, so it could not trigger this, but any future caller passing rich
  context could.

- **H2 — bearer token and bodies in release device logs** *(documented only)*.
  `http_service.dart:24-31`: `LogInterceptor(requestHeader: true, requestBody: true,
  responseBody: true)` is added unconditionally, and `debugPrint` is not stripped
  from release builds. Every request — including telemetry posts — logs its
  `Authorization: Bearer …` header (set at `token_interceptor.dart:24`) and full
  bodies to logcat/syslog on production devices. Recommendation: add the
  `LogInterceptor` only when `kDebugMode` is true. Not changed here because it
  alters logging behavior for the whole HTTP stack, beyond this audit's remit.

### Medium

- **M1 — wall-clock request timing** *(fixed)*.
  `timing_telemetry.dart` (pre-fix lines 156, 178): `TimingInterceptor` stamped
  `DateTime.now()` at request start and measured `DateTime.now().difference(start)`
  at completion. An NTP correction or manual clock change mid-request yields
  negative or wildly wrong durations that poison `total_ms`/`max_ms` for the whole
  window. Fixed by storing a running `Stopwatch` (monotonic) in `options.extra`.
  Timestamps on events themselves correctly use UTC wall clock
  (`telemetry.dart`, `timestamp` field) — appropriate for event times.

- **M2 — no offline queue, persistence, retry, or backoff** *(documented only)*.
  `telemetry.dart:55-81`: each event is one immediate POST; on any failure
  (offline, 500, timeout) the event is dropped with a debug log. There is no queue,
  so queue-bound/batching concerns are moot — but offline-heavy users contribute
  near-zero telemetry, and a failed `timing_report` loses its whole 2-minute window
  (aggregates are cleared at `timing_telemetry.dart:120-127` before delivery is
  attempted, with no retry). Acceptable as a documented design choice; if coverage
  on flaky networks matters, recommend a small bounded on-disk queue (the drift
  `app_database` and sync outbox already in base_sdk are natural homes).

- **M3 — unbounded per-window path cardinality** *(documented only)*.
  `timing_telemetry.dart:38,86`: `_requests` keys on raw `uri.path`. Paths that
  embed document IDs (e.g. `/api/resource/Order/ORD-123`) create one entry each —
  unbounded memory growth within a window and arbitrarily large payloads. This is
  also a mild privacy concern: document IDs travel inside `timing_report`.
  Recommendation: cap tracked paths per window (overflow into an `_other` bucket)
  and/or normalize ID-bearing segments.

- **M4 — timing reports pollute the backend error pipeline** *(documented only)*.
  `log_frontend_error.py:42,60-65`: every event becomes a Brain event prefixed
  `"Frontend Error: …"` via `record_event`. With PR #34, every active client now
  files a `"Frontend Error: timing_report"` roughly every 2 minutes — non-errors
  flooding an error-shaped pipeline, at per-event cost (one `frappe.call` each).
  Recommendation: branch on the event `type` server-side (route `timing_report`
  to metrics storage, not Brain), or give timings a dedicated whitelisted method.

- **M5 — flush requires activity; last window can be lost** *(documented only)*.
  `timing_telemetry.dart:96-98`: `_maybeFlush` runs only from a frame callback or a
  completed request. An app that goes idle and is then killed/backgrounded loses
  its final window. Recommendation: an `AppLifecycleListener` (or periodic timer)
  flush on pause/detach.

### Low

- **L1** — `telemetry.dart:22-24`: `generateTraceId` uses an unseeded per-call
  `math.Random()` with a 16-bit suffix; collisions are possible under bursts within
  the same microsecond. Cosmetic for a trace id; note the Next.js mirror uses
  32 bits (`telemetry.ts:33`).
- **L2** — `TraceIdInterceptor` (`telemetry.dart:28-34`) is dead code: nothing wires
  it; `token_interceptor.dart:19` duplicates the header logic. Recommend deleting
  one or wiring the interceptor and removing the duplicate.
- **L3** — `token_interceptor.dart:24`: `'Bearer  $token'` has a double space.
  Pre-existing and evidently tolerated by the backend; flagged, not changed.
- **L4** — `timing_telemetry.dart:113-115`: `avg_build_ms`/`avg_raster_ms`/`worst_ms`
  are JSON **strings** (`toStringAsFixed`) while sibling fields are ints — schema
  inconsistency for downstream numeric processing.
- **L5** — `http_service.dart:8`: `client()` constructs a brand-new `Dio` (plus four
  interceptors) per call, including for every telemetry flush. Pre-existing pattern;
  wasteful, not harmful.
- **L6** — payload `debugPrint` executed in release builds (now gated behind
  `kDebugMode` as part of the H1 fix, which also keeps payloads out of release logs).
- **L7** — singletons (`TelemetryClient.I`, `TimingTelemetry.I`) are per-isolate.
  Dart isolates share no state, so there is no data race; code touched here runs on
  the main isolate's event loop and mutates aggregates synchronously before any
  `await`, so no interleaving hazard. Background isolates would simply get their own
  empty aggregators.

### Privacy review

Client-sent payload is `{type, session_id?, timestamp, context}`; for `timing_report`
the context is endpoint paths, durations, and frame stats. No tokens, device
identifiers, file paths, or user content are placed in payloads by this code. The
two caveats: document IDs may ride along inside URL paths (M3), and the request
itself carries the user's bearer token — to the tenant's own backend only
(`AppConstants.baseUrl`, compile-time `BASE_URL`; no third parties). The dominant
privacy exposure is local, not on the wire: H2's release-build logging.

### Failure-mode review

- Delivery failures: swallowed (`telemetry.dart` catch-all; after the H1 fix this
  covers serialization too). Nothing rethrows into app code.
- Blocking: no synchronous I/O on the main path; the POST is async and unawaited by
  callers. `_maybeFlush` runs `jsonEncode` of the window payload inside a frame
  timings callback — bounded once M3's cap exists; fine today at normal cardinality.
- Recursion/feedback: telemetry's own POST is excluded from timing
  (`timing_telemetry.dart:85`), which also prevents flush-triggered flushes.
- Missing DI: `logError` no-ops when `HttpService` is unregistered
  (`telemetry.dart` `isRegistered` guard). `ensureFrameTracking` swallows the
  no-binding case and retries next request (`timing_telemetry.dart:51-59`).
- Full disk: nothing is written to disk by this path (no queue), so not applicable.

## Fixed in this PR

1. `telemetry.dart` — `logError` body fully wrapped in try/catch; payload encoded
   exactly once with a degrade-to-stub fallback for non-encodable context; debug
   trail gated behind `kDebugMode` (H1, L6).
2. `timing_telemetry.dart` — `TimingInterceptor` now times requests with a
   monotonic `Stopwatch` instead of wall-clock `DateTime` differences (M1).

## Recommended, not done here

- Gate `LogInterceptor` behind `kDebugMode` (H2) — highest-value follow-up.
- Bounded persistent queue with retry/backoff for events (M2).
- Path cardinality cap / ID normalization in `TimingTelemetry` (M3).
- Backend routing for `timing_report` out of the error/Brain pipeline (M4).
- Lifecycle-driven flush for the final window (M5).
- Remove or wire `TraceIdInterceptor`; unify with `TokenInterceptor` (L2).
- Numeric (not string) frame stats in the payload (L4).

## Integration notes — PR #34 (merged)

PR #34 (merge commit `212167f`, content commit `1cd9766`, merged
2026-08-13T22:57Z) routes per-endpoint request stats and frame timings through
`TelemetryClient.logError` as a single `timing_report` event per ~2-minute window.
The integration is correct as far as `TelemetryClient` is concerned: the payload is
JSON-safe (so H1 could not fire for it), the self-exclusion guard prevents timing
feedback loops, and `over_16ms` deliberately includes `over_33ms` frames. The
integration-level gaps are M1 (fixed), M3, M4, and M5 above — of these, M4 (every
client filing a non-error into the error pipeline every 2 minutes) deserves the
earliest attention as fleet size grows.

## Verification

`dart analyze` run on `base/dart` with Flutter 3.38.5 (results in the PR body).
`base/dart` has no test suite (none existed before this audit either).
