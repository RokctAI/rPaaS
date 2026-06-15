# API Reference: seller_marketing

Source file: `paas/api/seller_marketing/seller_marketing.py`

## Whitelisted API Endpoints

### `def get_seller_coupons(limit_start=0, limit_page_length=20)`
Retrieves a list of coupons for the current seller's shop.

### `def create_seller_coupon(coupon_data)`
Creates a new coupon for the current seller's shop.

### `def update_seller_coupon(coupon_name, coupon_data)`
Updates a coupon for the current seller's shop.

### `def delete_seller_coupon(coupon_name)`
Deletes a coupon for the current seller's shop.

### `def get_seller_discounts(limit_start=0, limit_page_length=20)`
Retrieves a list of discounts for the current seller's shop.

### `def create_seller_discount(discount_data)`
Creates a new discount for the current seller's shop.

### `def update_seller_discount(discount_name, discount_data)`
Updates a discount for the current seller's shop.

### `def delete_seller_discount(discount_name)`
Deletes a discount for the current seller's shop.

### `def get_seller_banners(limit_start=0, limit_page_length=20)`
Retrieves a list of banners for the current seller's shop.

### `def create_seller_banner(banner_data)`
Creates a new banner for the current seller's shop.

### `def update_seller_banner(banner_name, banner_data)`
Updates a banner for the current seller's shop.

### `def delete_seller_banner(banner_name)`
Deletes a banner for the current seller's shop.

### `def get_ads_packages()`
Retrieves a list of available ads packages.

### `def get_seller_shop_ads_packages(limit_start=0, limit_page_length=20)`
Retrieves a list of purchased ads packages for the current seller's shop.

### `def purchase_shop_ads_package(package_name)`
Auto-generated docstring for compliance.
