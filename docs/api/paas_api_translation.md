# API Reference: translation

Source file: `paas/api/translation.py`

## Whitelisted API Endpoints

### `def get_mobile_translations(lang=None)`
<!-- 512268c1cbed0cdff2080075cf58d498fafe6c23c271791fc8d2c8c97b2ab407 -->
The get_mobile_translations function retrieves translations for a specified language, defaulting to English if no language is provided. It takes one optional parameter, lang, which represents the target language for the translations. The function returns a dictionary containing the translation keys and their corresponding values, along with a success message.

### `def get_translations_paginate(search=None, group=None, locale=None, perPage=10, page=1, **kwargs)`
<!-- 03814f38160bc16866cd16b159c1c04e01b7a2190fdd8df322ad9edd1dc51b45 -->
The get_translations_paginate function retrieves a paginated list of translations based on the provided parameters. It accepts several arguments: search, group, locale, perPage, and page. The search parameter is used to filter translations by key or value, the group parameter filters by translation group, and the locale parameter filters by language locale. The perPage argument determines the number of translations to return per page, and the page argument specifies the current page number. The function returns a dictionary containing the total number of translations, the number of translations per page, and a dictionary of translations where each key is a unique translation key and the value is a list of translation details.

### `def create_translation()`
<!-- 56e6552291632898c75da2bdf1844c9f9b5a76bda5fd87122b05b95dafe119dc -->
The create_translation function is used to create a new translation entry in the database. It requires three parameters: group, key, and value, which are retrieved from the form dictionary. The group parameter specifies the translation group, the key parameter specifies the unique identifier for the translation, and the value parameter is a dictionary containing locale-text pairs. If the value parameter is provided as a string, it is attempted to be parsed as a JSON object. The function first deletes any existing translation with the same key, then creates new translation documents for each locale-text pair in the values dictionary. The function returns a success message if the operation is completed successfully, or an error message with a 400 status code if the parameters are invalid.

### `def update_translation(key=None)`
<!-- f5d07d53a9387f1ccecc4630eb8b470e3a2ef068a38a57e636ab03350dea5c30 -->
The update_translation function is used to update translations for a specific key in the system. It takes an optional key parameter, which defaults to None. If not provided, the function will attempt to retrieve the key from the form data. The function requires administrative privileges and expects the form data to contain a group and a dictionary of values, where each key represents a locale and the corresponding value is the translated text. If the provided values are in string format, the function will attempt to parse them as JSON. The function will delete any existing translations for the target key and then insert new translations based on the provided values. If any required parameters are missing or invalid, the function will return an error response. Otherwise, it will return a success message indicating that the translations have been updated successfully.

### `def delete_translation()`
<!-- 74f31be8861aa2a7ac22ce0b51f2354d573e9ca45f24d04f2c39a7a8356bc0d5 -->
The delete_translation function is used to delete translations from the system. It requires administrative privileges to execute. The function takes a single parameter, ids, which is expected to be a list of translation keys to be deleted. If the ids parameter is provided as a string, it is attempted to be parsed as a JSON list. If the ids parameter is invalid or empty, the function returns an error response. Otherwise, it iterates over the provided ids, retrieves the corresponding translation documents, and deletes them, ignoring any permission restrictions. Upon successful deletion, the function returns a success message.

### `def drop_all_translations()`
<!-- b47f58d9dcbadc53f7880beddb70ffe1afd70abdf05326fcab45e67924531f0a -->
The drop_all_translations function is used to delete all existing translations in the system. This function requires administrative privileges to execute. It retrieves a list of all translation documents, then iterates over the list to delete each document, ignoring any permission restrictions. Once all translations have been deleted, the function returns a success message indicating that the operation was completed successfully.

### `def truncate_translations()`
<!-- 1b99777fb4e91d2c57723f80aab58f1434d301eb43f5d791e2cc3038f8fb76c7 -->
The truncate_translations function is used to delete all existing translations in the system. It requires administrative privileges to execute. This function takes no parameters and returns a success message after truncation is complete. The purpose of this function is to reset the translation database, removing all existing records.

### `def restore_all_translations()`
<!-- 8a59527a1d0e40ed582bbbb01e18bec6b94a3b4aa862130a9b9158d8a230af26 -->
restore_all_translations – Restores all deleted PaaS Translation documents. The function first verifies that the caller has administrative privileges, then queries the “Deleted Document” table for entries where the deleted_doctype is “PaaS Translation” and collects their names. It iterates over each name, attempting to restore the document via frappe.model.api.restore_document; any exceptions raised during individual restores are silently ignored. The function takes no parameters and returns a standardized API success response containing the message “Successfully restored”.

### `def import_translations()`
<!-- d303840246e7ccfff6d34a49720a0416b3a8312041d4d63974ce85575150804c -->
The import_translations function is used to import translations from an uploaded file. It requires administrative privileges and expects a file to be uploaded, either in Excel (.xls, .xlsx) or CSV format. The file should contain columns for key, locale, and optionally value and group. The function then iterates over each row in the file, updating existing translations or creating new ones as necessary. If the import is successful, it returns a success message; otherwise, it returns an error message with the reason for the failure.

### `def export_translations()`
<!-- 5061128cfc06cd073a3f3790b49d3f5ce636ec50bfde91fe1b7723b4f9742bd0 -->
The export_translations function is used to export all translations from the system into an Excel file. It requires administrative privileges to execute. The function retrieves all translation data, including group, key, locale, and value, and saves it to an Excel file named translations_export.xlsx. If the Excel export fails, it attempts to export the data as a CSV file named translations_export.csv instead. The function returns a success message with the file path and name if the export is successful, or an error message if the export fails.
