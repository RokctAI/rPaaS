# telemetry_sdk (Next.js half)

Formal owner of the Next.js telemetry seam, mirroring `telemetry/dart`.

Per ADR-005 the one telemetry client every SDK may import lives in the shared
kernel — `base/nextjs/src/services/telemetry.ts`, installed into hosts at
`app/services/base/telemetry.ts` — because feature SDKs import only
`base_sdk`. This package owns the *lane*: WHEN/HOW events leave the browser
(the seam/config), while the client stays in base. Composing `telemetry_sdk`
into a Next.js shell's `composer.json` declares that the shell participates
in the telemetry lane.

It intentionally installs nothing today: `manifest.json` carries empty merge
blocks (`installs`/`dependencies`/`devDependencies`/`integrations`), exactly
like the dart half's manifest. Any future delivery-policy override (batching,
sampling, an alternate transport) belongs here, not in `base/nextjs`.

The frappe half (`core/telemetry/frappe`) is the backend: `api_error_log`
plus the `log_frontend_error` / `track_event` whitelisted methods.
