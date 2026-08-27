# orders_sdk (manager slice) — Frappe endpoint contract

What the ported Dart client calls, what exists server-side today, and what the
backend workstream still needs to close. This is a **deliverable of the
paas_manager fork, not a blocker on it** (revenue_sdk's
`frappe-endpoint-contract.md` pattern) — the Dart is ported, contracts are
declared on the facades, and unanswered calls fail visibly through
`ApiResult.failure`; nothing is stubbed or faked.

Source of the port: `paas_manager/lib/infrastructure/repositories/
{orders_repository,table_repository,users_repository,products_repository,
catalog_repository}.dart` (the W1 subset) — complete Dart implementations whose
only Laravel-specific part was the URL.

## SellerOrdersRepositoryFacade (`src/manager/infrastructure/repositories/seller_orders_repository.dart`)

| Call | Legacy path | Calls now | Exists today? |
|---|---|---|---|
| `getOrders` | `GET /api/v1/dashboard/seller/orders/paginate` (`status`, `date_from/to`, `page`) | `seller_order.get_seller_orders` (`limit_start/limit_page_length`, `status`, `from_date/to_date`) | **Yes** — but returns a flat order list (`name`, `user`, `grand_total`, `status`, `creation`), no `statistic` block and none of the nested order fields (`details`, `user`, `table`, `transaction`) the queue cards and details modal read. `OrdersPaginateResponse.fromJson` accepts the bare-list shape, so queues render and counters degrade to zero. **Gap: enrich payload + statistic block + `statuses[]` multi-filter.** |
| `getHistoryOrders` | same paginate with `statuses[]=delivered,canceled` | `get_seller_orders` with `status=delivered` | Partial — single-status only; canceled bucket missing until `statuses[]` lands. |
| `getOrderDetails` | `GET .../seller/orders/{id}` | `seller_order.get_seller_order_details` | **Yes** — verify nested shape (details/stock/addons/user/table/transaction) against `OrderData.fromJson`. |
| `updateOrderStatus` | `POST .../seller/order/{id}/status` | `seller_order.update_seller_order_status` | **Yes.** Wire statuses unchanged: `new/accepted/ready/on_a_way/delivered/canceled`. |
| `createOrder` | `POST /api/v1/dashboard/seller/orders` | `paas.api.order.order.create_order` (`order_data` = the legacy seller body verbatim) | Customer-shaped endpoint exists; **gap: seller-scoped create** (accepts `user_id`/`phone` for walk-in customer, `table_id` for dine-in, stock+addon lines). |
| `createTransaction` | `POST /api/v1/payments/order/{id}/transactions` | `paas.api.payment.create_order_transaction` | **Yes** — pay-side `wallet/frappe/src/api/payment/payment.py`, reached via the composed manifest alias `paas.api.payment.create_order_transaction` (`wallet/frappe/manifest.json` `whitelisted_methods`); `@idempotent` + content-level dedupe per order/gateway, amount and user read from the Order doc. |
| `getPayments` | `GET .../seller/shop-payments` | `paas.api.payment.payment.get_seller_shop_payments` | **No — gap** (POS filters the result to cash/wallet client-side). |
| `getCalculate` | `GET .../seller/order/products/calculate` (stock-list query) | `paas.api.order.order.get_products_calculate` | **No — gap** (FORK_MAPPING §3 Ask #6: existing `get_calculate` is cart-id based; POS needs the stock-list shape). Query contract preserved verbatim. |

## PosProductsRepositoryFacade (orders-owned; same endpoints as products_sdk)

| Call | Calls now | Exists today? |
|---|---|---|
| `getProducts` | `seller_product.get_seller_products_paginate` | **Yes** (products_sdk's contract; POS adds `active=1`, `status=published`). |
| `getShopCategories` | `seller_product.get_seller_categories` (`type=main`) | **Yes.** |
| `getProductDetails` | `seller_product.get_product_details` | **Yes.** |

## ADR-005 seams (host adapter `templates/adapters/manager/orders_adapters.dart`)

| Seam | Owner | Calls now | Exists today? |
|---|---|---|---|
| `PosSectionsTablesFacade.getSections` | merchants_sdk (S-11) | `seller_operations.get_seller_sections` | **No — gap** (seller_operations has menus/kitchens/receipts only). |
| `PosSectionsTablesFacade.getTables` | merchants_sdk (S-11) | `seller_operations.get_seller_tables` | **No — gap.** |
| `PosCustomersFacade.searchUsers` | users_sdk (S-2) | `paas.api.user.user.search_users` | users_sdk's `searchUser` exists — adapter swaps to the users_sdk Dart facade once S-2 merges. |
| `PosCustomersFacade.createUser` | users_sdk | `paas.api.user.user.create_walk_in_customer` | **No — the fork's recorded gap**: `register_user` is self-signup; no seller-creates-walk-in-customer endpoint. |

## Legacy `TableInterface` calls NOT carried over

The POS flow only lists sections/tables, so the narrow seam declares exactly
that. These legacy calls stay with the owning workstream (merchants/booking)
and are recorded here so they aren't lost: `createNewSection`, `createNewTable`,
`deleteSection`, `deleteTable`, `getTableInfo`, `getTableOrders`,
`disableDates`, `getBookings`, `setBookings`, `getWorkingDay`, `getCloseDay`,
`changeOrderStatus` (booking), table `getStatistic`.

## Twin-model dedup candidate (Rule 5 watch item)

ADR-005 forbids orders_sdk importing products_sdk, so the POS carries its own
`ProductData`/`Stock`/`CategoryData`/`AddonData` (in
`src/manager/infrastructure/models/`) — the same legacy classes products_sdk
ported as `SellerProductData`/`SellerStock`/`SellerCategoryData`/
`SellerAddonData`. Two SDKs now parse the same wire shape with parallel
classes. When a shared home exists (base_sdk models, or a commerce-common
package), collapse them; until then changes to the seller product wire shape
must touch both.
