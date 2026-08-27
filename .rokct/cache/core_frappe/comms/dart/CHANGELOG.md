# Changelog

## 1.9.0

* Broken-endpoint fix sweep: the notification, settings, and currencies
  repositories now call the backend through base_sdk's universal
  `PlatformGateway` (`api.notification.*`, `api.system.*`,
  `api.admin_content.get_admin_faqs`, `api.page.get_page` cmds — the
  comms/base `manifest.json` whitelisted-method aliases with the
  `{app_name}` segment dropped) instead of the previous direct
  `/api/method/paas.api.*` dotted paths, several of which pointed at
  module paths that do not exist in the composed app
  (`paas.api.user.user.*`, `paas.api.system.system.*`, short
  `paas.api.<fn>` names). `get_mobile_translations` is deliberately left
  as a direct call — its alias-key row belongs to the protocol
  lock-regen thread.

## 1.7.1

* Freezed 3 follow-through for the installed notification template (the fleet
  migration covered `lib/src` only): `NotificationState` migrated to the
  `abstract class` form and `notification_notifier.dart` given the direct
  `package:base_sdk/src/handlers/api_result.dart` import that brings the
  legacy `when`/`map` extensions into scope. No behavior change.

## 0.0.1

* TODO: Describe initial release.
