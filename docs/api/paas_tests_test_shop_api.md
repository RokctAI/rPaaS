# API Reference: test_shop_api

Source file: `paas/tests/test_shop_api.py`

## Classes

### class `TestShopAPI`

#### Documented Internal Methods
##### `test_create_shop_unauthorized(self)`
Test that a user without the Seller role cannot create a shop.

##### `test_create_shop_success(self)`
Test successful shop creation.

##### `test_get_shops_no_filters(self)`
Test fetching shops without any filters.

##### `test_get_shops_pagination(self)`
Test pagination for get_shops.

##### `test_get_shop_details_success(self)`
Test fetching details for a single, valid shop.

##### `test_get_shop_details_not_found(self)`
Test fetching details for a non-existent shop.

##### `test_get_shops_with_delivery_filter(self)`
Test fetching shops with delivery=True filter.

##### `test_get_shops_with_takeaway_filter(self)`
Test fetching shops with takeaway=True filter.

##### `test_get_shops_ordering(self)`
Test ordering of shops.
