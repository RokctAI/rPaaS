# API Reference: language

Source file: `paas/api/language/language.py`

## Whitelisted API Endpoints

### `def get_languages(active=True)`
Retrieves list of languages.

### `def get_default_language()`
Retrieves the default language.

### `def get_translations(locale, group=None)`
Retrieves translations for a specific locale, optionally filtered by group.
Returns a dictionary mapping keys to values, as expected by many frontends.
