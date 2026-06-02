# API Reference: banner

Source file: `paas/api/banner/banner.py`

## Whitelisted API Endpoints

### `def get_banners(page=1, limit_page_length=10)`
Fetches a paginated list of banners.

### `def get_banner(id)`
Fetches a single banner.

### `def get_ads(page=1)`
Fetches a paginated list of banners that are marked as ads.

### `def get_ad(id)`
Fetches a single banner that is marked as an ad.

### `def like_banner(id)`
Increments the 'likes' count on a banner.
