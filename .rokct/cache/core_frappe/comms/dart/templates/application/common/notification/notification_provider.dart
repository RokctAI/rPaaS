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


// Ported from paas_manager lib/application/notification/notification_provider.dart
// (comms_sdk manager consume, fork plan S-3 / migration bucket b).
// Resolution via base_sdk's injection getters: NotificationRepositoryFacade
// is registered by CommsSdkDependencies.register in the generated
// main.dart sdk-di block.
//
// Shared manager+driver template (driver migration S-D5): paas_driver's host
// twin resolved the same facade through its host dependency_manager
// (notificationRepo); base's injection getter is the SDK-side equivalent.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:base_sdk/src/di/injection.dart';

import 'notification_notifier.dart';
import 'notification_state.dart';

final notificationProvider =
    StateNotifierProvider<NotificationNotifier, NotificationState>(
  (ref) => NotificationNotifier(notificationRepo),
);
