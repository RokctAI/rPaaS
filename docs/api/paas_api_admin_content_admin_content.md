# API Reference: admin_content

Source file: `paas/api/admin_content/admin_content.py`

## Whitelisted API Endpoints

### `def get_admin_stories(limit_start=0, limit_page_length=20)`
Retrieves a list of all stories on the platform (for admins).

### `def get_admin_banners(limit_start=0, limit_page_length=20)`
Retrieves a list of platform-wide banners (for admins).

### `def create_admin_banner(banner_data)`
Creates a new platform-wide banner (for admins).

### `def update_admin_banner(banner_name, banner_data)`
Updates a platform-wide banner (for admins).

### `def delete_admin_banner(banner_name)`
Deletes a platform-wide banner (for admins).

### `def get_admin_faqs(limit_start=0, limit_page_length=20)`
Retrieves a list of all FAQs (for admins).

### `def create_admin_faq(faq_data)`
Creates a new FAQ (for admins).

### `def update_admin_faq(faq_name, faq_data)`
Updates an FAQ (for admins).

### `def delete_admin_faq(faq_name)`
Deletes an FAQ (for admins).

### `def get_admin_faq_categories(limit_start=0, limit_page_length=20)`
Retrieves a list of all FAQ categories (for admins).

### `def create_admin_faq_category(category_data)`
Creates a new FAQ category (for admins).

### `def update_admin_faq_category(category_name, category_data)`
Updates an FAQ category (for admins).

### `def delete_admin_faq_category(category_name)`
Deletes an FAQ category (for admins).
