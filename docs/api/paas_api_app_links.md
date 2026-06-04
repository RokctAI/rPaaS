# API Reference: app_links

Source file: `paas/api/app_links.py`

## Whitelisted API Endpoints

### `def get_assetlinks()`
<!-- 61af3adc8cb6972827c8d1efad1b970dcc2270c8cc17f5244c89047b280eaeab -->
The get_assetlinks function generates a JSON response containing asset links configuration for a Flutter app. It retrieves the package name and SHA256 fingerprints from the Flutter App Configuration settings, cleans up the fingerprints by removing empty lines or whitespace, and returns a list of asset links in the required format. The function returns an empty list if the package name is not set or if an error occurs during execution. The parameters for this function are implicitly defined by the configuration settings, specifically the package name and SHA256 fingerprints, which are used to construct the asset links configuration.

### `def get_apple_app_site_association()`
<!-- 4ecb63d9fd66b95d59f946f3236c0714d73fc662bfd0123e897f8d40627f5514 -->
The get_apple_app_site_association function generates the apple-app-site-association JSON object, which is used to enable Universal Links for an iOS application. This function retrieves the Apple team ID and iOS bundle ID from the Flutter App Configuration, constructs the app ID, and returns a JSON object containing the applinks details. The returned JSON object includes the app ID and specifies that all paths are supported. If the team ID or bundle ID is missing, or if an error occurs during execution, an empty dictionary is returned.
