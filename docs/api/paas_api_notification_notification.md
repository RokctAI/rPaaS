# API Reference: notification

Source file: `paas/api/notification/notification.py`

## Whitelisted API Endpoints

### `def send_push_notification(user, title, body, data=None)`
Sends a push notification to a specific user via FCM.

### `def get_default_sms_payload()`
Returns the default SMS payload from Push Notification Settings.

### `def get_notification_settings()`
Retrieves notification settings for the current user.
Returns a list of notification types with their active status.

### `def update_notification_settings(type, active)`
Updates the notification setting for a specific type.

### `def get_user_notifications(start=0, limit=20)`
Retrieves the list of notifications for the currently logged-in user.

### `def get_notification_count()`
Retrieves the count of unread notifications for the currently logged-in user.

### `def mark_notification_logs_as_read(ids=None)`
Marks specific notification logs as read.

### `def read_all_notifications()`
Marks all notifications as read for the current user.

### `def read_one_notification(name)`
Marks a single notification as read.
