# Hosting SDK — Frappe Half

The frappe half of the **hosting** SDK (the rPanel-based hosting product). It lives
in this repo alongside `telephony/frappe` — the other Service-category product
extracted from the control/rpanel stack — following the reuse-existing-SDK-repos
rule (tender → corporate, telephony → hardware).

## What is here today

A fixtures-only start:

- `src/fixtures/Subscription_Plan/` — the six hosting Subscription Plan seed
  records (Basic / Pro / Enterprise, Monthly + Yearly), byte-identical to the
  copies that shipped inside the rpanel app package at
  `rpanel/hosting/fixtures/Subscription_Plan` (RokctAI/rPanel#210).
- `src/fixtures/Item/` — the three hosting Item seed records referenced by
  those plans (a plan's referenced seed records travel with it).

## What joins later

The hosting module code (rPanel's `hosting` module) moves here as rpanel is
broken out of the control stack into SDK form, the same way control's telephony
surface moved into `telephony/frappe`. A `manifest.json` and composer wiring
join with it.

## How the fixtures are consumed

`src/fixtures/` is discovered by the control hub's cross-app Subscription Plan
fixture-dir scan (`control/control/utils/subscription_fixture_dirs.py` — the
union over every installed app's `<module>/fixtures/Subscription_Plan`), used by
both the plan seeder (`seed_subscription_plans_v4`) and the public plans API
(`get_subscription_plans`). The scan only sees this directory once the hosting
module is composed/installed on the site — which needs the `manifest.json` and
composer-template wiring above. Until then these fixtures are inert (fixture-dark)
and the hub's already-seeded Subscription Plan DB rows keep serving the hosting
plans, exactly as with telephony's fixtures before its wiring landed.
