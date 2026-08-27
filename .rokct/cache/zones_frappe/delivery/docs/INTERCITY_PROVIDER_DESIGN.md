# Intercity Delivery — Logistics Provider Integration Design

## Overview

The delivery module gains a second fulfilment mode alongside the existing
driver network:

| Mode | Doctype flow | Fulfilled by | Range |
|---|---|---|---|
| **Last-mile** (existing) | `Parcel Order` → deliveryman | Platform driver network (delivery SDK) | Within a delivery zone |
| **Intercity** (new) | `Parcel Order` → logistics provider | Third-party couriers via provider API (first: ShipRazor) | City-to-city / national |

Providers are integrated exactly like payment providers: a common interface, a
per-tenant settings doctype that selects and configures the active provider(s),
and provider-specific adapters behind it. The client apps never talk to the
provider — only to our API.

## Provider abstraction

```
delivery/frappe/src/providers/
    base.py          # DeliveryProvider abstract interface
    shiprazor.py     # first implementation
    registry.py      # resolves configured provider for a booking
```

`DeliveryProvider` interface (mirrors the payment-provider pattern):

- `get_quote(parcel)` — rates/options for a from/to + dimensions + declared value
- `create_shipment(parcel)` — book, returns waybill/tracking references
- `cancel_shipment(ref)`
- `get_tracking(ref)` / `handle_webhook(payload)` — status updates mapped onto
  `Parcel Order.status`
- `register_pickup_location(address)` / `delete_pickup_location(ref)` — see
  lifecycle below

Provider credentials (single ShipRazor API key) live server-side in a
`Delivery Provider Settings` doctype. **The key is never exposed to Dart/Next.js
clients and no client is ever given ShipRazor access** — this is a hard
compliance requirement (ShipRazor Merchant Agreement clause 1.2: no sharing of
login or right-to-use; our platform is the sole interface).

## Parcel Order changes

- `fulfilment_mode`: `last_mile` (default) | `intercity`
- `provider`, `provider_shipment_ref`, `waybill_no`, `tracking_url`
- `declared_value` (required for intercity — liability caps key off it)
- `cod_amount` (optional; reconciliation, see below)
- Existing `address_from` / `address_to` / `phone_*` / `username_*` fields are
  reused as the canonical addresses; they are user-linked in our DB and are
  the source of truth — provider-side records are derived and ephemeral.

## Ephemeral pickup-location ("warehouse") lifecycle

ShipRazor models every collection point as a named "warehouse". We do not
mirror thousands of client addresses into ShipRazor. Instead:

1. **Book**: when an intercity `Parcel Order` is submitted, derive a
   deterministic reference from the normalized collection address, e.g.
   `RKT-{user_id}-{sha1(normalized_address)[:8]}`.
2. **Ensure**: if no live provider-side warehouse exists for that reference,
   create it via the API; store the mapping in a `Provider Pickup Location`
   doctype with a **reference count** of in-flight shipments using it.
3. **Ship**: create the shipment against that warehouse.
4. **Release**: on terminal status (delivered / cancelled / RTO-complete via
   webhook), decrement the refcount. When it reaches zero, delete the
   provider-side warehouse and mark the mapping inactive.

Guardrails:

- **Refcounting, not per-parcel delete** — two parcels collecting from the same
  client address share one provider warehouse; deleting after the first
  delivery would strand the second.
- **Grace period** — optionally delay deletion (e.g. 24h after refcount hits 0)
  so a client shipping daily from the same address doesn't churn
  create/delete calls; the deterministic reference makes re-creation cheap
  either way.
- **Orphan sweep** — scheduled job reconciles provider-side warehouses against
  active mappings and deletes leftovers (covers missed webhooks/crashes).
- **RTO awareness** — a returned parcel needs the origin warehouse until the
  return closes; RTO statuses hold the refcount.

## Compliance guardrails baked into the flow

These enforce the back-to-back Terms (`INTERCITY_DELIVERY_TERMS.md`):

- **Prohibited-items gate**: parcel category/description validated against the
  provider's prohibited/restricted list before booking is accepted.
- **Declared value required**; quotes and optional transit cover keyed off it;
  liability messaging in the client apps states the R5,000 / declared-value /
  recovered-amount cap.
- **Evidence capture at collection**: signed manifest + parcel photo captured
  into the parcel record at pickup, so upstream claim deadlines (3 days at
  ShipRazor, 48h for our clients) can actually be met.
- **COD reconciliation**: per-parcel COD ledger; client remittance only after
  provider remittance lands; set-off against outstanding fees supported.
- **Invoice dispute clock**: provider invoices surfaced to finance within 24h
  (upstream dispute window is 7 days; ours to clients is 5).

## Out of scope for this document

Rate-shopping across multiple providers, cross-border flows, and ShipGuard
pass-through product configuration — each follows the same provider interface
and can be layered on without schema changes.
