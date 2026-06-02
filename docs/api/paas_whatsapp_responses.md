# API Reference: responses

Source file: `paas/whatsapp/responses.py`

## Documented Module Functions

### `def send_message(wa_id, payload)`
Sends a payload to the Meta Graph API.

### `def send_shop_list(wa_id, shops)`
Sends a List Message with available shops.

### `def send_category_list(wa_id, categories, shop_id)`
Sends a List Message with shop categories.

### `def send_product_list(wa_id, products)`
Sends a List Message with products.

### `def send_product_card(wa_id, product)`
Sends an Image Message with Buttons (Add, Customize).

### `def send_product_flow(wa_id, product, flow_id)`
Sends a WhatsApp Flow for product customization.

### `def send_cart_summary(wa_id, session)`
Sends a text summary of the cart with a 'Checkout' button.

### `def send_static_map_confirmation(wa_id, lat, long)`
Generates and sends a static map image for location confirmation.
