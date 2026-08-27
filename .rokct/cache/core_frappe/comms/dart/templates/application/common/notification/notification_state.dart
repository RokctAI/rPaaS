// Copyright (c) 2026 RokctAI
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.


// Ported from paas_manager lib/application/notification/notification_state.dart
// (comms_sdk manager consume, fork plan S-3 / migration bucket b), models
// swapped for their base_sdk twins (NotificationModel lives in base's
// notification_response.dart; CountNotificationModel in
// count_of_notifications_data.dart).
//
// Shared manager+driver template (driver migration S-D5): paas_driver's host
// twin declares the identical four fields. notification_state.freezed.dart
// is deliberately not shipped — the host's own build_runner pass regenerates
// it after install.
import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:base_sdk/src/models/data/count_of_notifications_data.dart';
import 'package:base_sdk/src/models/response/notification_response.dart';

part 'notification_state.freezed.dart';

@freezed
abstract class NotificationState with _$NotificationState {
  const factory NotificationState({
    @Default([]) List<NotificationModel> notifications,
    @Default(null) CountNotificationModel? countOfNotifications,
    @Default(false) bool isReadAllLoading,
    @Default(false) bool isAllNotificationsLoading,
  }) = _NotificationState;

  const NotificationState._();
}
