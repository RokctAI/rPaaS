# revenue_sdk — Frappe endpoint contract

What the ported Dart client calls, what exists server-side today, and what the
backend workstream still needs to close. This is a **deliverable of the
paas_manager fork, not a blocker on it** — the Dart is ported and the contract
is declared on `SellerStatisticsRepositoryFacade`; the endpoints catch up
separately.

Source of the port: `paas_manager/lib/infrastructure/repositories/users_repository.dart`
(`getStatistics`, `getStatisticsOrder`). Those were complete Dart
implementations; only the server answering the URL was the legacy one.

---

## 1. `getStatistics` — income page header, tiles and earnings chart

| | |
|---|---|
| **Client calls** | `GET /api/method/paas.api.seller_report.seller_report.get_order_report` |
| **Query** | `from_date` (`yyyy-MM-dd`), `to_date` (`yyyy-MM-dd`), `type` (`day`) |
| **Legacy path this replaces** | `GET /api/v1/dashboard/seller/order/report` with `date_from` / `date_to` / `type` |
| **Exists today?** | **Yes**, `commerce/merchants/frappe/src/api/seller_report/seller_report.py:7` |
| **Signature today** | `get_order_report(from_date=None, to_date=None)` — defaults to the last month, delegates to `get_seller_sales_report` |

**Gap.** The endpoint exists and accepts the date window, but returns a flat
list of orders (`name`, `user`, `grand_total`, `status`, `creation`). The client
expects the aggregate `StatisticsModel`:

| Field the client reads | Needed for | Present server-side? |
|---|---|---|
| `total_count` | "Total orders" tile | derivable |
| `total_today_count` | "today" sub-line | **no** |
| `total_new_count` | "New orders" tile | **no** — see note |
| `total_accepted_count` | "Accepted orders" tile | **no** — see note |
| `total_ready_count` | order-state breakdown | **no** |
| `total_on_a_way_count` | order-state breakdown | **no** |
| `total_canceled_count` | "Cancelled" tile | yes, as `cancel_orders_count` on the *other* endpoint |
| `total_delivered_count` | "Delivered" tile | yes, as `delivered_orders_count` on the *other* endpoint |
| `total_price`, `fm_total_price` | earnings header | partially — `total_earned` on the other endpoint |
| `last_order_total_price`, `last_order_income` | last-order row | **no** |
| `chart[]` (`time`, `total_price`) | **the earnings chart** | **no** |

**Note on New/Accepted.** The adjacent
`seller_reports.get_seller_statistics()` does return counters, but collapses
`New` + `Accepted` + `Shipped` into a single `progress_orders_count`, and takes
**no date range at all** (every figure is shop-lifetime). So it cannot back this
page even as a partial substitute. The two endpoints should probably converge.

**Client behaviour meanwhile.** `StatisticsResponse.fromJson` accepts either a
`message` (Frappe) or `data` (legacy) envelope, and every field is nullable, so
an endpoint returning a subset degrades to zeros rather than throwing. The
earnings chart is already behind an `isNotEmpty` guard in `income_page.dart`, so
it simply does not render until `chart[]` arrives. Nothing is stubbed or faked.

---

## 2. `getStatisticsOrder` — "more orders" paginated list

| | |
|---|---|
| **Client calls** | `GET /api/method/paas.api.seller_report.seller_report.get_order_report_paginate` |
| **Query** | `from_date`, `to_date`, `page`, `per_page` |
| **Legacy path this replaces** | `GET /api/v1/dashboard/seller/orders/report/paginate` with `date_from` / `date_to` / `page` / `perPage` |
| **Exists today?** | **Yes**, `seller_report.py` — `get_order_report_paginate` |

**Gap.** Row shape. The client's `StatisticsOrder` expects `id`, `status`,
`firstname`, `lastname`, `active`, `quantity`, `price`, `products[]`.
`get_seller_sales_report` supplies `name`, `user`, `grand_total`, `status`,
`creation` — so the customer name is unsplit, and `quantity`, `products[]` and
`active` are absent. Pagination parameters also need confirming: the current
implementation takes only `from_date` / `to_date`.

---

## Summary for the backend workstream

1. `get_order_report` should return the aggregate statistics shape (counters +
   `chart[]` series) for the requested window, not a raw order list.
2. Per-status counters must stay **unmerged** — the income page has distinct
   New / Accepted / Ready / On-a-way / Delivered / Cancelled tiles.
3. `get_order_report_paginate` needs `page` / `per_page` and the richer row
   shape (split name, line quantity, product titles).
4. Consider whether `seller_reports.get_seller_statistics` and
   `seller_report.get_order_report` should be one endpoint; today they overlap
   in intent, disagree on shape, and only one accepts a date range.
