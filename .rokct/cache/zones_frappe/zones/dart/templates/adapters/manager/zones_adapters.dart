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

import 'package:zones_sdk/src/manager/infrastructure/repositories/delivery_zones_repository.dart';

/// Host-side wiring for zones_sdk in the manager flavour (ADR-005).
///
/// Thin by design (manager migration M5): the shop-polygon endpoint knowledge
/// that used to live behind the host's users repository
/// (`package:manager/domain/di/dependency_manager.dart`) moved into
/// zones_sdk's own [ManagerDeliveryZonesRepository], so no host-owned
/// repository remains. This file is still host-composition code — it lives in
/// templates/ and is installed at compose time (manager flavour only, see
/// manifest.json app_type.manager), which is why it may deep-import zones_sdk
/// role code. The validator scans SDK lib/ only, so nothing here is a
/// cross-SDK import violation.
///
/// Registration is injected into the generated main.dart by the manifest's
/// app_type.manager `di_hooks` entry (isRegistered-guarded):
///
///   GetIt.instance.registerLazySingleton<DeliveryZonesFacade>(
///     () => ManagerDeliveryZonesAdapter());
///
/// Without it deliveryZoneProvider falls back to a 501 "not wired" stand-in
/// and the zone screen never reaches real shop data.
///
/// No ZoneEditPolicy registration, deliberately: a merchant drawing their own
/// shop's catchment has no equivalent of the driver's
/// `driver_can_edit_credentials` restriction, and registering nothing is the
/// contract's explicit way to say "unrestricted".
class ManagerDeliveryZonesAdapter extends ManagerDeliveryZonesRepository {}
