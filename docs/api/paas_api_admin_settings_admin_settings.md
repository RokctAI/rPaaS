# API Reference: admin_settings

Source file: `paas/api/admin_settings/admin_settings.py`

## Whitelisted API Endpoints

### `def get_all_languages(limit_start=0, limit_page_length=20)`
Retrieves a list of all languages (for admins).

### `def update_language(language_name, language_data)`
Updates a language (for admins).

### `def get_all_currencies(limit_start=0, limit_page_length=20)`
Retrieves a list of all currencies (for admins).

### `def update_currency(currency_name, currency_data)`
Updates a currency (for admins).

### `def get_email_settings()`
Retrieves the email settings (for admins).

### `def update_email_settings(settings_data)`
Updates the email settings (for admins).

### `def get_all_email_templates(limit_start=0, limit_page_length=20)`
Retrieves a list of all email templates on the platform (for admins).

### `def update_email_template(template_name, template_data)`
Updates an email template (for admins).

### `def get_email_subscriptions(limit_start=0, limit_page_length=20)`
Retrieves a list of all email subscriptions on the platform (for admins).

### `def create_email_subscription(subscription_data)`
Creates a new email subscription (for admins).

### `def delete_email_subscription(subscription_name)`
Deletes an email subscription (for admins).

### `def get_general_settings()`
Retrieves the General Settings (Settings Doctype).

### `def update_general_settings(settings_data)`
Updates the General Settings.

### `def get_app_settings()`
Retrieves the App Settings.

### `def update_app_settings(settings_data)`
Updates the App Settings.
