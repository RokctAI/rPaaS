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

import 'package:base_sdk/base_sdk.dart';
import 'package:zones_sdk/zones_sdk.dart';
import 'package:zones_sdk/src/driver/infrastructure/repositories/delivery_zones_repository.dart';
import 'package:zones_sdk/src/driver/infrastructure/repositories/demo_delivery_zones_repository.dart';

/// Host-side wiring for zones_sdk in the driver flavour (ADR-005).
///
/// Thin by design (driver migration M4, mirroring the manager adapter): the
/// courier-profile endpoint knowledge that used to live behind the host's
/// user repository (`package:${package}/domain/di/dependency_manager.dart`)
/// moved into zones_sdk's own [DriverDeliveryZonesRepository], so no
/// host-owned repository remains. This file is still host-composition code —
/// it lives in templates/ and is installed at compose time (driver flavour
/// only, see manifest.json app_type.driver), which is why it may deep-import
/// zones_sdk role code. The validator scans SDK lib/ only, so nothing here is
/// a cross-SDK import violation.
///
/// Both registrations are injected into the generated main.dart by the
/// manifest's app_type.driver `di_hooks` entry (isRegistered-guarded):
///
///   GetIt.instance.registerLazySingleton<DeliveryZonesFacade>(
///     () => DriverDeliveryZonesAdapter());
///   GetIt.instance.registerLazySingleton<ZoneEditPolicy>(
///     () => DriverZoneEditPolicy());
///
/// Without them deliveryZoneProvider falls back to a 501 "not wired" stand-in
/// and the zone screen never reaches real profile data.
class DriverDeliveryZonesAdapter extends DriverDeliveryZonesRepository {
  /// Demo builds (`--dart-define=IS_DEMO=true`) serve the fictional offline
  /// zone instead of hitting the profile endpoint — the same
  /// `AppConstants.isDemo` split delivery_sdk's `DriverDeliveryDependencies`
  /// applies to every courier facade. The gate lives here (not in the
  /// repository) so the SDK's HTTP class stays a pure production path and
  /// the swap sits exactly where the flavour is composed, next to the
  /// registration that injects it. Zero behavior change when IS_DEMO is off.
  static final DeliveryZonesFacade _demo = DemoDriverDeliveryZonesRepository();

  @override
  Future<ApiResult<List<List<double>>>> fetchDeliveryZones() =>
      AppConstants.isDemo
          ? _demo.fetchDeliveryZones()
          : super.fetchDeliveryZones();

  @override
  Future<ApiResult<void>> updateDeliveryZones({
    required List<List<double>> points,
  }) =>
      AppConstants.isDemo
          ? _demo.updateDeliveryZones(points: points)
          : super.updateDeliveryZones(points: points);
}

/// The driver flavour's rule for who may redraw a zone.
///
/// Operators who assign routes centrally set `driver_can_edit_credentials` to
/// "0", making the zone map read-only. A missing setting means allowed — the
/// permissive default matches pre-fork behaviour, where the flag had to be
/// explicitly "0" to lock editing.
///
/// Host-side rather than in zones_sdk: this setting is a driver-app concept,
/// and a merchant editing their own shop catchment has no equivalent
/// restriction. Registering nothing is how a flavour says "unrestricted".
class DriverZoneEditPolicy implements ZoneEditPolicy {
  @override
  bool canEdit() {
    for (final setting in LocalStorage.getSettingsList()) {
      if (setting.key == 'driver_can_edit_credentials') {
        return setting.value != '0';
      }
    }
    return true;
  }
}
