# API Reference: upload

Source file: `paas/api/upload/upload.py`

## Whitelisted API Endpoints

### `def upload_file(file, filename=None, is_private=0)`
Uploads a file and returns the file URL.

### `def upload_multi_image(files=None, upload_type=None, doc_name=None, lang='en')`
Uploads multiple images and attaches them to a specific document.
