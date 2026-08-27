## 1.9.4

* Routed the broken direct `/api/method/paas.api.*` call sites through
  base_sdk's universal platform gateway (`PlatformGateway`, fleet rule
  2026-08-15): shops repository (`api.shop.search_shops`/`get_shops`/
  `get_nearby_shops`/`get_shops_by_ids`/`create_shop`/`get_shops_recommend`,
  cross-module `api.cart.join_order`, `api.delivery.check_delivery_zone`,
  `api.story.get_story`, `api.tag.get_tags`, `api.product.get_suggest_price`)
  and the offline shop-create sync handler (`api.shop.create_shop`,
  idempotency header preserved). Fixed payload keys that never matched the
  backend kwargs: get_shops_by_ids `shop_ids`, join_order
  `cart_id`/`user_name`, create_shop wrapped in `shop_data`. Registered the
  missing `api.seller_operations.get_seller_sections`/`get_seller_tables` and
  `api.seller_product.create_product` whitelisted-method keys in
  merchants/frappe/manifest.json. Recorded endpoint gaps
  (get_shop_by_uuid/get_shop_branch/get_pickup_shops) are untouched.

## 1.9.3

* Freezed 3 follow-through (PR #28 missed the templates dir): the installed
  `merchants_adapters.dart` template now imports
  `package:base_sdk/src/handlers/api_result.dart` directly so its
  `ApiResult.when` call site resolves against freezed-3 base_sdk. No behavior
  change.

## 1.9.1

* Sliced `manager/infrastructure/models/` into the canonical `data/` and `response/` subfolders: moved `sections_tables.dart` to `models/data/` and `my_shop_response.dart` to `models/response/`. Updated all imports. No API changes.

## 1.9.0

* Driver migration S-D6: adopted paas_driver's intro-story block (`driver/application/story` + story page + `/story` route). See manifest comment for details.
