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

import 'package:auto_route/auto_route.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:get_it/get_it.dart';

import 'package:base_sdk/src/handlers/api_result.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:revenue_sdk/revenue_sdk.dart'
    show CourierStatisticsRepositoryFacade, CourierStatisticsResponse;

import 'package:${package}/presentation/routes/app_router.dart';

/// Host-composition seam between delivery_sdk's courier profile/home pages
/// and revenue_sdk's courier earnings facade.
///
/// paas_driver's legacy `profileSettingsProvider` carried this fetch
/// directly, which would make delivery_sdk import revenue_sdk — feature SDKs
/// import only base_sdk, so the earnings read lives in this installed file
/// instead: host code may reach into any composed sibling SDK (revenue_sdk
/// is part of every driver compose, driver.json), and the profile/home
/// templates read it via their `${package}` import of this file.
class CourierProfileStatisticsState {
  final bool isLoading;
  final CourierStatisticsResponse? statistics;

  const CourierProfileStatisticsState({
    this.isLoading = false,
    this.statistics,
  });

  CourierProfileStatisticsState copyWith({
    bool? isLoading,
    CourierStatisticsResponse? statistics,
  }) =>
      CourierProfileStatisticsState(
        isLoading: isLoading ?? this.isLoading,
        statistics: statistics ?? this.statistics,
      );
}

class CourierProfileStatisticsNotifier
    extends StateNotifier<CourierProfileStatisticsState> {
  final CourierStatisticsRepositoryFacade _courierStatistics;

  CourierProfileStatisticsNotifier(this._courierStatistics)
      : super(const CourierProfileStatisticsState());

  /// Port of the legacy `fetchProfileStatistics` (401 handling included:
  /// a dead session logs out and lands on /login, host route classes are
  /// fine here because this is host code).
  Future<void> fetchProfileStatistics({required BuildContext context}) async {
    state = state.copyWith(isLoading: true);
    final response = await _courierStatistics.getCourierStatistics();
    response.when(
      success: (data) {
        state = state.copyWith(statistics: data, isLoading: false);
      },
      failure: (failure, status) {
        if (status == 401) {
          LocalStorage.logout();
          context.router.popUntilRoot();
          context.replaceRoute(const LoginRoute());
        } else {
          state = state.copyWith(isLoading: false);
          AppHelpers.showCheckTopSnackBar(
            context,
            AppHelpers.getTranslation(failure),
          );
        }
      },
    );
  }
}

final courierProfileStatisticsProvider = StateNotifierProvider<
    CourierProfileStatisticsNotifier, CourierProfileStatisticsState>(
  (ref) => CourierProfileStatisticsNotifier(
    GetIt.instance.get<CourierStatisticsRepositoryFacade>(),
  ),
);
