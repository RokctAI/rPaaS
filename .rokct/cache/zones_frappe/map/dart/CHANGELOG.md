## Unreleased

* Google Places lookups now go through base_sdk's `HttpService` client
  instead of a bare `Dio()` instance, so they ride the standard interceptor
  chain — timing telemetry and ADR-006 trace-id stamping. `requireAuth: false`
  keeps the tenant bearer token off the third-party host (radio_sdk audit-2
  precedent).

## 0.0.1

* TODO: Describe initial release.
