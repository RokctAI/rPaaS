## 1.8.0

* 18+ (adults only) checkout support. `get_calculate` now answers the
  additive `contains_adult_items` / `requires_birth_date` flags (parsed by
  base_sdk's `GetCalculateModel`), and the order sheet's `_createOrder` gains
  an age gate mirroring the phone-gate precedent: when the cart holds an
  adult item and the profile has no birth date, a date-of-birth bottom sheet
  (`AgeVerifyModal`) collects it, writes it through the universal platform
  gateway (`api.user.update_user_profile`, `birth_date` "YYYY-MM-DD"), then
  re-runs calculate + order creation. The backend `create_order` failure
  markers `AGE_VERIFICATION_REQUIRED` and `UNDERAGE_PURCHASE_BLOCKED` are
  mapped in the customer orders repository onto distinct friendly,
  translatable messages (wire-key strings, declared in the manifest's
  customer tr_keys). Manager POS orders are exempt server-side (face-to-face
  ID check), so the POS flow is untouched.

## 1.7.1

* Routed the broken direct `/api/method/paas.api.*` call sites through
  base_sdk's universal platform gateway (`PlatformGateway`, fleet rule
  2026-08-15): cart (`api.cart.*` — get/add/remove/change_status/delete_cart/
  delete_user/get_cart_in_group), customer orders (`api.order.*` —
  create/list/details/review/cancel/get_calculate), coupon
  (`api.coupon.check_coupon`), parcel (`api.parcel.*` — review/types/
  calculate_price/create/list/single), seller POS create-order + offline sync
  handler (`api.order.create_order`, idempotency header preserved), seller
  shop payments (`api.seller_transactions.get_seller_shop_payments`), and the
  manager POS adapters (`api.seller_operations.get_seller_sections`/
  `get_seller_tables`, keys registered in merchants/frappe/manifest.json).
  Fixed payload keys that never matched the backend kwargs: check_coupon
  `code`/`shop_id`, get_calculate `coupon_code`, tip_process `tip_amount`,
  get_driver_location `driver_id`, add_parcel_review `parcel_id`/`review`,
  calculate_price nested `address_from`/`address_to`. Alias-only paths
  (`paas.api.repeating_order.*`, `paas.api.user.*`,
  `paas.api.payment.create_order_transaction`) and recorded endpoint gaps
  are untouched.

## 1.6.2

* Freezed 3 follow-through for the pockets PR #28 missed: `OrdersBoardState`,
  `CanceledOrdersState`, and `DeliveredOrdersState` migrated to the
  `abstract class` form, and their notifiers given the direct
  `package:base_sdk/src/handlers/api_result.dart` import that brings the
  legacy `when`/`map` extensions into scope. No behavior change.

## 1.6.1

* Rewrite the last three double-segment API call paths in
  `orders_repository.dart` to their registered composed manifest aliases
  (same client-side fix direction as pay PR #9 and the 1.5.2
  `create_order_transaction` rewrite):
  `paas.api.payment.payment.initiate_<gateway>_payment` →
  `paas.api.payment.initiate_<gateway>_payment` (pay wallet manifest
  registers the flutterwave/paypal/paystack initiate aliases), and
  `paas.api.user.user.create_order_refund` /
  `paas.api.user.user.get_user_order_refunds` → `paas.api.user.…`
  (users manifest aliases). The old double-segment paths 404 on composed
  backends. No behavior change beyond the URLs; the documented-gap
  endpoints (`get_seller_shop_payments`, templates' `search_users` /
  `create_walk_in_customer`) are intentionally untouched.

## 1.6.0

* Wide-screen (POS-style) layouts for the manager order pages, gated on
  base_sdk >= 1.11.0's adaptive primitives (`AdaptiveShell`, `SplitPane`,
  window-size classes — core PR #35 must land first). Compact/medium windows
  are byte-for-byte the old phone flows.
* Order queues: on expanded windows `orders_home_page` swaps the four-icon
  tab bar for a six-column kanban board (new / accepted / ready / on the way /
  delivered / canceled — POS's `board_view` minus its cooking column). Cards
  long-press-drag forward along the state machine using Flutter's own
  `LongPressDraggable`/`DragTarget` (no `drag_and_drop_lists` dependency, no
  host pubspec change); a drop calls the same `updateOrderStatus` repository
  call as the details modal's swipe button (new `ordersBoardProvider`), then
  refreshes the source and target columns. The four active columns reuse the
  existing per-status providers; new `deliveredOrdersProvider` /
  `canceledOrdersProvider` back the two history columns (manifest gains the
  `delivered`/`canceled` tr_keys for their headers).
* Create order: on expanded windows the product grid and the cart render
  side-by-side (`SplitPane`, POS `main_page` style). The cart body moved from
  `order_page.dart` into a shared `OrderPane` widget that both the pushed
  phone route and the embedded pane use on the same cart/payment providers;
  the embedded pane recalculates when the cart's stocks change instead of on
  route push.
* `NewOrdersNotifier` only calls `requestRefresh()` when the pull-to-refresh
  controller is attached to a scroll view — on the board no SmartRefresher
  exists and the unguarded call would throw.

## 1.5.2

* Offline POS sale payments: `OrderCreateSyncHandler._createTransaction`
  now sends an `X-Idempotency-Key` header (`<op.id>:txn` — derived from
  the same op id as the order-create call but deliberately distinct, so
  the two creates never share a key). Pairs with the pay-side
  `create_order_transaction` endpoint landing (called via its composed
  manifest alias `paas.api.payment.create_order_transaction`); the two
  call sites that used the unregistered 4-segment
  `paas.api.payment.payment.create_order_transaction` path are rewritten
  to the alias (same client-side fix direction as pay PR #9).
  The contract doc's `createTransaction` row is flipped from gap to done
  and the stale "Recorded gap" comment in `seller_orders_repository.dart`
  is updated. Best-effort semantics of the transaction call unchanged.

## 1.5.1

* Fix the manager shipping address page template (composes to
  `lib/presentation/pages/create_order/shipping/shipping_address_page.dart`):
  the six `IntlPhoneField` underline borders referenced the legacy `Style`
  class inside `const BorderSide(...)`, breaking the paas_manager APK build
  ("Not a constant expression", Build (Smart) run 31698905702). Renamed to
  base_sdk's `AppStyle.differBorderColor` and dropped `const` from the
  affected `BorderSide`s, matching the zones#16 courier de-const pattern.

## 0.0.1

* TODO: Describe initial release.
