# API Reference: webhook

Source file: `paas/whatsapp/api/webhook.py`

## Whitelisted API Endpoints

### `def webhook()`
Main entry point for WhatsApp Webhooks.
Handles verification (GET) and messages (POST).

## Documented Module Functions

### `def verify_webhook()`
Handles the Meta Webhook Verification Challenge.

### `def process_webhook()`
Processes incoming messages from Meta.
