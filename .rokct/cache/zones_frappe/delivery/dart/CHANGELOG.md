## 1.10.1

* FIXED Windows driver build dying before its first frame: the
  `delivery-driver-courier-location-workmanager` boot hook ran an
  unguarded `await Workmanager().initialize(callbackDispatcher);` in the
  composed `main()` before `runApp`. workmanager only ships Android/iOS
  implementations, so on a composed Windows exe the call threw
  "No implementation found for workmanager on this platform" and the app
  exited with no window (taskbar icon flash only). The hook body is now
  wrapped in the fleet boot-hook guard idiom (Android/iOS platform
  allowlist + fail-open try/catch with a debugPrint, same shape as
  comms' firebase-fcm boot hook) - desktop and web skip the courier
  background tracker, which they never supported anyway. No behavior
  change on Android/iOS.

## 1.10.0

* Driver order ids migrated int -> String (the fleet-wide docname
  migration's last straggler; the customer path was already done).
  Order docnames are Frappe default hash strings (the commerce Order
  doctype has no autoname), so the driver flavor's `int? orderId`
  surface could only ever address numerically-named orders:
  * `OrderDetailData.id`, `Details.orderId` and `PushModel.orderId` are
    now `String?`; `fromJson` prefers the always-present `name` key and
    falls back to the legacy numeric `id` for older payloads.
  * `CourierOrdersRepositoryFacade` / `CourierParcelRepositoryFacade`
    and their HTTP + demo implementations now take String order/parcel
    ids throughout (base_sdk's `ParcelOrder.id` was already a String —
    the parcel templates were round-tripping it through `int.tryParse`,
    which nulled out every hash docname).
  * FIXED silent delivered no-op: `deliveredFinish` (and the parcel
    twin) used to send `orderId ?? 0` — on a hash docname the serializer
    emits `id: null`, so the driver marked the order delivered while the
    backend updated nothing. A null id now aborts with a logged error
    instead of sending 0, and the delivered status update's result is
    checked, surfacing backend failures to the courier.
  * Wire-compatible: the backend endpoints are untyped and
    `serialize_deliveryman_order` already always emits `name` (its
    numeric-only legacy `id` emission is kept for old builds) — no
    frappe changes.
  * Demo seed order ids became strings ("900001"), matching real
    docnames end-to-end in demo mode.

## 1.9.2

* Driver ID verification for 18+ orders (`contains_adult_items`, the
  additive flag the commerce module stamps on orders with adult
  products):
  * `OrderDetailData` gains `containsAdultItems` (backend key
    `contains_adult_items`, absent-when-false, defaults to false), so
    old payloads keep parsing unchanged.
  * Upfront notice: the driver `OrderItem` component - rendered on the
    order card and in the delivery bottom sheet - shows an
    "ID required, recipient must be 18+" banner on flagged orders, so
    the courier knows BEFORE arriving at the customer.
  * Completion gate: every delivered path (plain, cash collection,
    record-as-credit) now funnels through a required
    "Check recipient's ID: 18 or older?" confirm dialog on flagged
    orders (cash-collection dialog precedent); only on confirm does
    `deliveredFinish` run, threading `recipient_age_verified: true`
    through `updateOrder` into the gateway payload. Only the yes/no
    confirmation travels - no ID image or document data is ever
    captured or stored.
  * Backend counterpart: map's `update_driver_order_status` accepts the
    OPTIONAL `recipient_age_verified` param and refuses to complete a
    flagged order without it (`AGE_VERIFICATION_REQUIRED`); delivery's
    `serialize_deliveryman_order` emits the additive
    `contains_adult_items` key (weather_notice absent-when-false
    precedent). Old driver builds keep working for all non-adult orders;
    flagged orders require a recomposed app - intended enforcement.
  * New driver tr_keys: `idRequired18Plus`, `checkRecipientId18Plus`.

## 1.8.0

* Courier home: severe-weather heads-up banner. The home bottom sheet
  (`templates/pages/driver/home/bottom_sheet_screen.dart`) now renders
  weather_sdk's `weatherWarningsBanner` through base_sdk's
  `EmbeddedWidgets.I` seam (ADR-005 - no weather_sdk import), docked just
  above the fixed-height sheet card so a variable-height notice can never
  overflow it.
  * Fail-closed by construction: the seam call is dispatched dynamically
    inside a try/catch because weather_sdk is optional in courier
    compositions - without it the host's `EmbeddedWidgets` has no
    `weatherWarningsBanner` implementation (base_sdk's interface does not
    declare the method either, so a static call would not even compile)
    and `noSuchMethod` throws; the guard turns that into
    `SizedBox.shrink()`, so the courier home renders nothing extra and
    never crashes. When weather_sdk IS composed, the banner itself renders
    nothing unless there is an active notice.
  * The banner resolves the courier's own position via the
    `WeatherSdkConfig.locationResolver` wired by weather_sdk 1.4.0's new
    driver-flavor template (base_sdk's selected-address slot, which
    `CourierStorage.saveSelectedLocation` keeps at the courier's live map
    position).

## 1.7.2

* Repointed the driver repositories' remaining legacy
  `/api/v1/dashboard/*` call sites that have a real Frappe equivalent to
  the versioned method surface:
  * orders repository: `setCurrentOrder`, `uploadImage` and `setOrder`
    (attach) now go through the universal platform gateway to the map
    module's whitelisted driver_order defs
    (`api.driver_order.set_current_order` / `.upload_order_image` /
    `.attach_order_to_me` — the map manifest registers those alias keys
    in this wave); `cancelOrder` goes through the gateway to the
    registered `api.driver_order.update_driver_order_status` (the alias
    1.7.1 added), same as its sibling `updateOrder`.
    `setOrder` answers an empty `OrderDetailModel` on success (the def's
    raw doc dict is not OrderDetailData-shaped and the only caller
    ignores it); `cancelOrder`'s legacy `note` is not persisted (the def
    takes no note kwarg — known gap).
  * parcel repository: `setCurrentOrder`, `addReviewParcel` and
    `setParcel` (attach) now go through the universal platform gateway
    to the delivery module's whitelisted driver_parcel defs
    (`api.driver_parcel.set_current_parcel_order` /
    `.add_parcel_order_review` / `.attach_parcel_order_to_me` — alias
    keys the delivery manifest registers in this wave).
  * courier repository: `setOnline` goes through the universal platform
    gateway to the registered `api.delivery_man.
    update_deliveryman_settings` method, expressing the legacy
    server-side toggle as the explicit desired value from the same
    `CourierStorage` cache its caller flips on success.
* Sites with NO registered Frappe equivalent or a genuine payload/shape
  mismatch were deliberately left on their (dead) legacy paths and are
  listed as decision items in zones PR #30: available/history/current
  order+parcel lists, single order/parcel show, order review,
  deliveryman settings (get + vehicle update), profile update,
  request-models (get + create) and the courier delivery-zone polygon
  read/write.

## 1.7.1

* Routed every driver call site added in the 1.6.0 (COD) and 1.7.0
  (routing) waves through base_sdk's universal platform gateway
  (`PlatformGateway`, per the 2026-08-15 fleet rule): the old direct
  `/api/method/paas.api.*` dotted paths become prefix-free gateway cmds
  (`api.driver_order.*`, `api.driver_parcel.*`, `api.dispatch_route.*`,
  `api.delivery_man.get_deliveryman_settings`, `api.driver.update_location`)
  mirroring the owning modules' `manifest.json` whitelisted-method keys.
  GET-style reads (`get_driver_orders_paginate`, `get_driver_route`,
  `get_my_dispatch_route`, `get_deliveryman_settings`) become gateway
  POSTs. The Workmanager background-isolate location report builds the
  same gateway request by hand (no DI in that isolate) against
  `kPlatformGatewayPath`. Registered the two whitelisted-method manifest
  keys the gateway needs to dispatch the status updates
  (`api.driver_order.update_driver_order_status` in map,
  `api.driver_parcel.update_driver_parcel_order_status` in delivery) —
  they were only reachable by their direct composed dotted paths before.
  Pre-existing legacy `/api/v1/*` calls are untouched.

## 1.7.0

* Driver route optimization wave:
  * New "My Route" page (`/driver-route`, launched from a route button on
    the courier home map): numbered, server-ordered stop cards — label,
    stop type, leg distance, per-stop quantity+unit, "Cash to collect"
    chip — with the next pending stop highlighted; tapping a stop hands
    off to `map_launcher` (existing MapsList sheet). The backend
    (`get_driver_route`) is authoritative for ordering: greedy
    nearest-next from the driver's position, pickups before their own
    drop-offs, coordinate-less stops flagged at the tail.
  * Admin-composed Dispatch Routes (Pickup or Delivery mode, per-stop
    quantities — the water-run case) surface on the same page via
    `get_my_dispatch_route`; dispatch stops carry Done / Skip actions
    (`complete_dispatch_stop`) and the list re-fetches (and re-orders)
    after every completion.
  * Rewired `getActiveOrders` from the dead legacy
    `/api/v1/dashboard/deliveryman/orders/paginate` path to the working
    `get_driver_orders_paginate` Frappe endpoint (now returning
    data+meta with parsed coordinates, nested shop and payment tag);
    `OrderDetailData.id` parses tolerantly since Frappe names are
    strings.
  * Rewired courier location reporting (10-minute Workmanager background
    task + foreground `setCurrentLocation`) from the dead legacy
    `/api/v1/dashboard/deliveryman/settings/location` path to
    `paas.api.driver.driver.update_location` with
    `{latitude, longitude}` — this position seeds the route optimizer.
  * New driver tr_keys: `myRoute`, `pickupRoute`, `deliveryRoute`,
    `noRouteStops`, `noLocationForStop`, `quantity`.

## 1.6.0

* Driver COD (cash-on-delivery) wave:
  * Prominent "Cash to collect" line on cash orders in the courier order
    card, the push-order sheet and the delivery bottom sheet (tag ==
    'cash' via `order.transaction?.paymentSystem?.tag`).
  * Delivered flow on cash orders now confirms the amount actually
    received (prefilled with the order total, editable) after the
    proof-of-delivery photo and BEFORE `deliveredFinish`; a failed
    backend confirm keeps the dialog open so the order is never
    delivered-but-unrecorded. Drivers whose `can_convert_cod_to_credit`
    capability is enabled get a secondary "Record as credit" action.
  * Parcel delivered flow: parcels with a sender-declared
    `codAmount` (base_sdk ParcelOrder) show "Collect from recipient" and
    confirm the collected cash (backend settles deliveryman wallet ->
    sender wallet) before `deliveredFinishParcel`.
  * Rewired `updateOrder` / `updateParcel` status posts and the new COD
    endpoints from the dead legacy `/api/v1/dashboard/deliveryman/*`
    surface to the Frappe `/api/method/paas.api.*` convention; new
    `getDeliverymanSettingsRaw()` reads the per-driver capability flag
    without touching the legacy `DeliveryResponse` model.
  * New driver tr_keys: `cashToCollect`, `codConfirmed`,
    `collectFromRecipient`, `howMuchCashReceived`, `recordAsCredit`.

## 1.5.0

* Post-compose APK fix round for paas_driver (Build (Smart) run 31635788470,
  87 Dart compile errors), courier vertical aligned with the shared kernel:
  * `ImageCropperMarker` -> base_sdk's `ImageCropperForMarker` (same class,
    base's name; the courier pages already imported base's
    `marker_image_cropper.dart`, only the identifier was stale).
  * Selected-location storage: the legacy host stored a bare `LatLng` under
    `keyAddressSelected`; base's `LocalStorage.setAddressSelected` takes an
    `AddressData`. New `CourierStorage.saveSelectedLocation(LatLng)` wraps
    the coordinates in `AddressData.location`, and reads go through the new
    `AddressData.latitude`/`longitude` getters (base_sdk 1.9.0).
  * Language flow: `LanguageScreen(afterUpdate:)` (host-era widget, never
    composed) -> `EmbeddedWidgets.I.languageScreen(onSave:)` (comms_sdk's
    embedded widget, manager precedent) +
    `AppNotifier.changeLocale` instead of the host's `changeLanguage`.
  * `Delayed` import (base_sdk `tpying_delay.dart`) in the home page.
  * Dropped the host-era no-op args base's helpers never had:
    `AppHelpers.numberFormat(maxLength:)` (self-assigned, dead in the old
    host too) and `showCustomModalBottomSheet(isExpanded:)` (accepted but
    unused in the old host).
  * `ParcelOrder.id` is `String?` in base (commerce/orders consumes it as
    String); the courier notifier's `int?` params now get `int.tryParse` at
    the four call sites.
  * De-consted widgets using brand-mutable `AppStyle.primary`/`shimmerBase`
    (order_history, parcel_history, bottom_sheet_screen, orders_item,
    rate_customer, underline_bordered_text_field, edit_car — commerce#18
    story_page precedent) and const-qualified shop_avarat's default
    `Color` value.
  * Manifest: `confirmPasswordDoesntMatchWithNewPassword` tr_key (used by
    edit_profile_modal, absent from base).

## 1.4.0

* (retro note; shipped without a CHANGELOG entry) `app_routes`
  replaceMainRoute -> /home for driver composes; courier location boot
  hooks (zones PR #14).

## 1.3.0

* Courier vertical build-out (S-D3 of the paas_driver lib-regenerable plan):
  `lib/src/driver/` role slice ported from paas_driver main — application
  slices (home map, orders, parcels, push-order, driver, vehicles, profile),
  the Laravel deliveryman repositories moved AS-IS (decision D2:
  `CourierOrdersRepository`, `CourierParcelRepository`, `CourierRepository`
  over `/api/v1/dashboard/deliveryman/*`), courier-only models, and
  `DriverDeliveryDependencies` (di hook, revenue_sdk precedent).
* Driver templates installed to the exact host paths paas_driver's tracked
  router/pages import today: pages (home ×10, orders, order history, parcels
  ×3, parcel history, push order, profile ×7 incl. the new
  `courier_statistics_provider.dart` revenue seam, become-driver shell),
  components ×14 (incl. restaurant_item / product_item / maps_list per
  decision D3 and seven custodianship copies of driver-only widgets), and
  `delivery_adapters.dart` (vehicle-capture adapter).
* Manifest: real `home_page` template (the key existed since 1.2.0 without
  the file), `home_sdk` flag, `app_type.driver` routes for
  /home /orders /order-history /parcels /parcel-history /profile
  /become-driver, `session_policy` (deliveryman → /home, `*` fallback →
  /become-driver pending decision D1 / auth_sdk S-D4), the
  `delivery.vehicle_details` registration step (`VehicleDetailsSlide`,
  decision D5 scope: the legacy become-driver form's fields only),
  `app_routes` (replaceLoginRoute), 31 courier `tr_keys`, `asset_keys`
  (pngMyLocation, svgBalance) + custodianship asset copies.

## 1.2.0

* (pre-existing) delivery points repository, delivery/become-driver common
  pages, splash/marker custodianship assets.
