# Recon: repository and ecosystem (severe-weather early-warning groundwork)

Date: 2026-08-19. Line numbers refer to the revisions pinned below; zones paths are relative
to the zones repo root.

## Revisions examined

| Repo | Revision |
|---|---|
| RokctAI/zones | `56dc49749e81b8a5a384ad4ee5eca7c92d29aebd` (2026-08-17, "Merge pull request #34 from RokctAI/claude/hearth-thread-wcmaq8") |
| RokctAI/the-rokct-protocol | `77f8588af9b3ab6f024c84237fd8abcfaa1f9617` |
| RokctAI/shared-workflows | `3059fd2212521a2e7ca04dcf6a726b72f31263fa` |

---

## (a) Platform gateway call pattern (client side)

`weather/dart/lib/src/common/infrastructure/services/weather_service.dart`
lines 197–224 (`_fetchWithRetry`) — verbatim core:

```dart
      // Every client-facing backend call POSTs the single universal
      // platform gateway ([kPlatformGatewayPath], imported from base_sdk)
      // with a `{"cmd": ..., "payload": ...}` envelope; [cmd] is the
      // weather manifest's whitelisted-method key minus the app segment
      // ([WeatherSdkConfig.weatherCmd]). The base client owns the tenant
      // base URL and (via TokenInterceptor) the bearer token. ...
      final response = await _dio(requireAuth: true).post<dynamic>(
        kPlatformGatewayPath,
        data: {'cmd': cmd, 'payload': payload},
      );
```

- `kPlatformGatewayPath` comes from `package:base_sdk/src/handlers/platform_gateway.dart`
  (import at line 29). It is NOT defined in the zones repo. SDK_ECOSYSTEM.md
  lines 244–247 states the concrete URL: clients POST
  `/api/v1/method/rokct.platform.api` with a prefix-free `cmd` — never
  `/api/method/paas.<module>...`.
- The cmd is set in `weather/dart/lib/src/common/config/weather_sdk_config.dart`
  line 70: `static String weatherCmd = 'tenant.api.get_weather';` — i.e. the
  frappe manifest's whitelisted-method key with the `{app_name}.` segment dropped.
- Call sequence: shop lat/lng → GeoNames reverse geocode (`requireAuth: false`,
  lines 108–149, default fallback `'messina,za'`) → gateway POST with
  `{'location': 'city,cc'}` payload (lines 174–195), 3 retries with linear
  backoff (lines 197–253).

### Frappe manifest mapping

`weather/frappe/manifest.json` (entire file, 10 lines):

```json
{
  "name": "weather",
  "description": "Modular backend package for weather integration features",
  "hooks": {
    "whitelisted_methods": {
      "{app_name}.tenant.api.get_weather": "{app_name}.weather.weather.get_weather.get_weather",
      "{app_name}.tenant.api.set_weather_alias": "{app_name}.weather.weather.set_weather_alias.set_weather_alias"
    }
  }
}
```

- Key = client-facing alias (`{app_name}` + prefix-free cmd). Value = real composed
  dotted path: module dir `weather` (manifest `name`) + the `src/` tree
  (`src/weather/get_weather/get_weather.py` → `{app}/weather/weather/get_weather/get_weather.py`).
- The composer (`the-rokct-protocol/core/utils/frappe/compose_backend.py`,
  `merge_hooks()` at line 901) writes each alias under BOTH
  `whitelisted_methods` (back-compat, ~line 995) and
  `override_whitelisted_methods` (lines 1007–1018) — the latter is the only key
  frappe's dispatcher (`frappe.override_whitelisted_method` in
  `handler.execute_cmd`) actually reads. So an alias in the manifest is all it
  takes for the cmd to resolve at dispatch time after compose.

### Backend implementation

`weather/frappe/src/weather/get_weather/get_weather.py`:
- Lines 31–32: cross-module imports use the token — `from {app_name}.comms.tenant_utils import send_tenant_email`, `from {app_name}.core.helpers import *` (raw file is a compose template, not valid Python — expected).
- Lines 35–49: `def get_weather(location: str)`; tenant-side cache key
  `weather_proxy_{location...}` via `frappe.cache().get_value`.
- Lines 52–69: reads `frappe.conf` `control_plane_url` / `api_secret` /
  `control_plane_scheme`, calls
  `{scheme}://{control_plane_url}/api/method/control.control.api.get_weather`
  with headers `X-Rokct-Secret` + `X-Rokct-Tenant`.
- Line 79: caches response `expires_in_sec=600` (10 minutes). Confirms the
  "10-min cached proxy" assumption.
- `set_weather_alias.py` (same dir pattern): POST proxy to
  `control.control.weather.set_weather_alias`, with a local-learning fallback
  via `frappe.call` when the control plane is not configured (lines 44–52).

**Surprise:** neither weather function carries `@frappe.whitelist()`, while
every sibling module's API functions do (e.g.
`map/frappe/src/api/driver_order/driver_order.py:130`,
`delivery/frappe/src/api/delivery/delivery.py:50` — some `allow_guest=True`).
Frappe checks `is_whitelisted()` on the resolved function after the
override rewrite, so a NEW endpoint should be decorated `@frappe.whitelist()`
— and the missing decorator on the existing two is worth flagging upstream.

---

## (b) Frappe manifest schema; declaring a new endpoint + scheduled job that activates by merge alone

Schema (from `the-rokct-protocol/core/utils/frappe/frappe_sdk_management.md`):
- Top-level: `name`, `description`, `dependencies` (pip names appended to the
  shell's requirements.txt/pyproject.toml), `hooks`, optional `app_type`
  persona blocks (doc lines 86–141).
- `hooks` supports (via `merge_hooks`, doc line 126–128 and
  compose_backend.py 901+): `whitelisted_methods`, `doc_events`,
  `scheduler_events`, `fixtures`, `auth_hooks`, `before_uninstall`,
  `after_install`, `commands`.
- Exactly two tokens substituted in `.py/.js/.html/.json` under `src/` and
  `doctype/`: `{app_name}` (target shell package) and `{module_name}`
  (manifest `name`). Nothing else is touched; a leftover token after compose
  is a lint warning (hard error under `ROKCT_COMPOSE_STRICT=1`).
- DocTypes: `doctype/<dt>/` at module root (its JSON `"module"` key force-
  rewritten to manifest name; convention `"module": "{module_name}"`), or
  src-nested `src/**/doctype/`. Duplicate module-root DocType dirs across
  modules = hard error.

Live scheduled-job precedent in this repo —
`delivery/frappe/manifest.json` lines 99–106:

```json
    "scheduler_events": {
      "hourly": [
        "{app_name}.delivery.providers.lifecycle.process_due_pickup_releases"
      ],
      "daily": [
        "{app_name}.delivery.providers.lifecycle.sweep_orphan_pickup_locations"
      ]
    }
```

with the implementations at
`delivery/frappe/src/providers/lifecycle.py` (functions at
lines 145 and 176) — confirming `src/<subpath>` composes to
`{app}/<module_name>/<subpath>`.

`scheduler_events` also supports a `"cron"` bucket keyed by cron expression
(compose_backend.py lines 933–973; expression validated by regex
`^[\w*/,\- ]+$`, croniter syntax — line 231 comment and `_HOOK_VALUE_PATTERNS`).
All dotted handler values are regex-validated (`^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$`)
before being embedded in the composed hooks.py — no arbitrary strings.

So for a new severe-weather capability, "activates by merge alone" means:
1. Add `src/weather/<new_endpoint>/...py` (function decorated
   `@frappe.whitelist()`), plus scheduled-task function(s) anywhere under `src/`.
2. In `weather/frappe/manifest.json`, add the alias under
   `hooks.whitelisted_methods` (`{app_name}.tenant.api.<cmd>` →
   `{app_name}.weather.<src-path>.<func>`) and the job under
   `hooks.scheduler_events` (hourly/daily/cron with `{app_name}`-tokenized
   dotted paths).
3. Merge to `main` — the weather module is already in both frappe composer
   templates (`core/utils/frappe/composer/rcore.json` and
   `deliveryplatform.json`, entry
   `{name: weather, enabled: true, git: RokctAI/zones, path: ../zones/weather/frappe, ref: main}`),
   so the next backend compose picks it up; no template edits needed for an
   addition inside the existing module. (Client propagation: weather_sdk is in
   flutter templates `pos.json` line 148, `manager.json`, `launch_manager.json`;
   the sdk-bump-poller in shared-workflows fires dependent shell builds on any
   `dart/manifest.json` version change — SDK_ECOSYSTEM.md lines 249–262.)

The frappe manifest has no `version` field — versioning rides the dart manifest (see (e)).

## (c) `sdk_validator.py --compliance` — every enforced rule

`shared-workflows/scripts/sdk_validator.py` (631 lines).
Discovery: walks `--root` (default `$GITHUB_WORKSPACE` in CI, else the
multi-repo workspace parent of shared-workflows) for `manifest.json` files
whose path contains `dart` (skipping node_modules/.next/.kilo/.rokct) —
lines 136–149. Per SDK it runs:

1. **Consumers advisory** (lines 578–586, never failing): names consuming
   shells from the protocol's `sdk_consumers.json` when reachable.
2. **Structure check** — `validate_structure()` lines 211–335. Base is
   `dart/lib/src` (fallback `dart/`); scans `common/` plus persona sibling
   dirs the SDK's own manifest declares under `app_type`; split SDKs are
   checked combined (ANY path satisfies a rule):
   - `application/` missing → WARNING; present but with no feature subfolders
     → ERROR; empty subfolder → WARNING (lines 271–284).
   - `infrastructure/models/`, if it exists, must contain `data/` and
     `response/` slices → missing slice ERROR; loose files directly in
     models/ → WARNING (lines 291–301).
   - Singular `infrastructure/repository` → ERROR (must be plural
     `repositories`) (lines 307–310).
   - `di/` missing (with files) → ERROR (lines 321–322).
   - `infrastructure/database` missing while the manifest declares the
     `database` key → ERROR (lines 323–326).
   - `infrastructure/repositories` missing → WARNING; `domain/interface`
     missing → WARNING (lines 327–333).
   - (`infrastructure/services` and `utils` are minority patterns — not
     checked at all.)
3. **Manifest import validation** (lines 594–610 + `extract_imports`
   415–441 + `validate_import` 452–487): every `package:...` string in
   structured manifest fields (all `_comment*` keys skipped) must resolve —
   `${package}/<path>` must be installed by some SDK's `installs` (top-level
   or app_type flavor) or be composer-generated
   (`presentation/routes/app_router.dart`); `package:<sdk>/...` must name a
   discovered SDK containing that filename. Violations → ERROR.
4. **ADR-005 cross-SDK import check** — `validate_cross_sdk_imports()` lines
   350–412: regex `^\s*(?:import|export)\s+['"]package:(\w+)/` over every
   `.dart` under `lib/` (templates/ deliberately NOT scanned). Allowed: own
   package, `base_sdk` (the sole allowlist entry, line 342), true third-party.
   Import of another discovered SDK → ERROR; unknown `*_sdk` package in
   per-repo mode → heuristic WARNING.
5. **`--compliance` only**: `run_compliance_scanner()` lines 96–134 runs
   `shared-workflows/scripts/compliance_scanner.py` with cwd = the SDK's
   `dart/` dir and `EVIDENCE_REPO_DIR=<sdk root>`; FAIL if output contains
   `ARCHITECTURAL COMPLIANCE FAILED: N`. The scanner is an AST/static gate of
   ~50 checks in 18 layers (`scripts/compliance/README.md`) over
   `.py/.ts/.tsx/.dart/.conf/.yml/.yaml`/nginx/dockerfile files (generated
   `.g.dart/.gr.dart/.freezed.dart` excluded); error-severity findings exit 1,
   warnings don't block; per-repo `compliance.config.json` can exclude/retune;
   it refuses to run on composed app shells (composer.json or
   `.rokct/config/app_type` marker) unless `COMPLIANCE_FORCE=1`; `GROQ_API`
   only gates the post-pass AI doc generation. Evidence lands under
   `.rokct/evidence/` (zones repo already has that dir).

Note: sdk_validator only parses `<sdk>/dart/manifest.json` — it does not
validate frappe manifests. The frappe side is validated at compose time
(token lint, hook-value regexes, duplicate-DocType detection).

## (d) SDK_ECOSYSTEM.md hard invariants relevant to extending weather/

From `the-rokct-protocol/SDK_ECOSYSTEM.md` lines 310–342
("Hard invariants") plus surrounding rules:

1. **ADR-005** (line 310): feature SDKs import only `base_sdk`; cross-SDK
   needs = consumer-defined interface in `domain/interface/` + host-app
   adapter wired in `templates/`. weather_sdk currently complies (only
   base_sdk imports).
2. **Backward compatibility across consumers** (line 337): shells compose at
   `ref: "main"`, so a breaking merge silently breaks every consumer at next
   compose. weather is composed into pos, manager, launch_manager shells
   (flutter) and rcore/deliveryplatform (frappe). Additions must be additive;
   any breaking change ships consumer fixes in the same change-set.
3. Dart `manifest.json` is **authoritative** for version and declarations
   (lines 48–50); pubspec version is frequently stale (true here: manifest
   1.2.1 vs pubspec 1.2.0).
4. Cross-module frappe imports use `{app_name}`; same-module imports relative;
   never hardcode `paas.`/`rcore.` (lines 214–247). Clients never build
   app-prefixed URLs — everything through the gateway.
5. Composer templates in the protocol repo are canonical (lines 206–212,
   410–412); editing only an app's committed composer.json gets clobbered by CI.
6. One `session_policy`/`brand_hook` declarer per app; apps track zero `lib/`
   files; PlatformStack never learns about SDKs (invariants 2, 4–6) — not
   triggered by a weather-internal addition, but these constrain any
   FCM/alert-push ambition (push wiring lives in boot_hooks/di_hooks of
   whichever SDK owns it).
7. Any NEW protocol-repo file that consumers fetch-and-execute must be added
   to `protocol.lock.json` (lines 279–281) — not applicable to a zones-repo
   change.

## (e) Versioning rules

- Bump `weather/dart/manifest.json` `version` (currently `1.2.1`) **in the
  same commit** as any SDK change, and update the SDK's CHANGELOG
  (SDK_ECOSYSTEM.md lines 249–252, 400–401).
- Propagation is automatic: `shared-workflows/.github/workflows/sdk-bump-poller.yml`
  polls every 10 min, diffs `*/dart/manifest.json` versions, dispatches
  dependent shells' build.yml (lines 253–259). No hookup files.
- **Gap found:** `weather/dart/CHANGELOG.md` does not exist (only
  `delivery/dart/CHANGELOG.md` and `map/dart/CHANGELOG.md` exist in the zones
  repo). The ecosystem doc requires per-SDK changelogs — the extension work
  should create it.
- The frappe manifest carries no version; the dart manifest bump is what
  drives rebuild propagation even for backend-only changes (the frappe side
  activates on next backend compose of the shells regardless).

## (f) install.py / sha256 pin findings

- `weather/dart/install.py` exists (as it does for delivery/map/zones dart
  SDKs): a 36-line shim that appends `.rokct` to sys.path (with a
  path-containment guard) and calls
  `sdk_installer_base.install_sdk_files_and_routes('weather_sdk')`.
- **It is NOT sha256-pinned.** `protocol.lock.json` (ref
  `b5af34fae1ae6ee0d0951d3902f398e9620a8fed`) pins only protocol-repo
  toolchain files (`core/utils/flutter/sdk_composer.py`,
  `sdk_installer_base.py`, `core/utils/frappe/compose_backend.py`, etc.);
  no `install.py` appears in it, and no `composer.json` exists anywhere in
  the zones repo (it is an SDK monorepo, not a shell — compliance_scanner
  even uses root composer.json as the "app shell" marker to refuse scanning).
- sha256 mentions inside zones are only `.rokct/initiate.py`,
  `.rokct/end_protocol.py`, `.rokct/sync_workspace.py` — truncated
  (`hexdigest()[:16]`) self-sync/freshness checks, not integrity pins on SDK
  files.
- Implication: modifying `weather/dart/install.py` needs no lockfile flow;
  only new fetch-and-execute files in the protocol repo would.

## (g) Surprises / risks

1. **Missing `@frappe.whitelist()`** on both existing weather endpoints
   (get_weather.py:35, set_weather_alias.py:35) while every other module
   decorates its API functions. Either these are currently broken behind the
   gateway or whitelisting is applied by some shell-side mechanism not in
   this repo. A new endpoint must be decorated; do not copy this omission.
2. **Missing weather/dart/CHANGELOG.md** despite the same-commit
   changelog rule.
3. **pubspec (1.2.0) vs manifest (1.2.1) skew** — documented as normal;
   manifest wins. Don't "fix" pubspec as part of unrelated work.
4. **Unused/odd imports in the frappe sources** (pytz, requests,
   create_custom_field, complete_setup_wizard, `{app_name}.comms`,
   `{app_name}.core.helpers` star-import at get_weather.py:21–32, plus a
   no-op trace-id line 40). The star-import means the composed shell must
   contain `comms` and `core` modules — a hidden module dependency. New files
   should import only what they use.
5. **The control-plane leg is out of reach from this repo**:
   `control.control.api.get_weather` lives elsewhere. A tenant-side scheduled
   early-warning job can only consume what that endpoint returns
   (weatherapi.com-shaped current+3-day payload) unless the control plane
   also changes.
6. **The weather module is dual-composed** (rcore.json AND deliveryplatform.json
   frappe templates) — a scheduler job merged into the manifest will run on
   both shell products. Design idempotent, cheap jobs.
7. `weather/nextjs/` contains only a `.gitignore` — an empty placeholder
   (census in SDK_ECOSYSTEM.md line 102 agrees: nextjs "—").
8. Compose hook values are regex-validated and repr-embedded — scheduler
   dotted paths must be pure dotted identifiers; cron keys must match
   `^[\w*/,\- ]+$`.
