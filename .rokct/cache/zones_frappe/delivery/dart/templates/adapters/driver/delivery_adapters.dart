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

import 'package:flutter/foundation.dart';
import 'package:get_it/get_it.dart';

import 'package:base_sdk/src/domain/interface/gallery.dart';
import 'package:base_sdk/src/handlers/api_result.dart';
import 'package:base_sdk/src/services/enums.dart';

import 'package:delivery_sdk/src/driver/di/driver_delivery_di.dart';
import 'package:delivery_sdk/src/driver/domain/interface/courier.dart';
import 'package:delivery_sdk/src/driver/presentation/widgets/vehicle_details_slide.dart';

/// Host-side wiring for delivery_sdk's driver registration seam (ADR-005;
/// the merchants `merchants_adapters.dart` precedent).
///
/// delivery_sdk owns the vehicle-details step widget ([VehicleDetailsSlide])
/// that its manifest `registration_steps` entry injects into auth_sdk's
/// post-register pipeline, and declares [CourierVehicleCapture] in its own
/// terms; this installed host-composition file supplies the adapter that
/// lands the capture on [CourierRepositoryFacade.createCarInfo]
/// (`/api/v1/dashboard/user/request-models` — the become-a-courier request).
/// This file lives in templates/ and installs into the app at compose time
/// (driver flavour only, see manifest.json app_type.driver), which is why it
/// may reach into delivery_sdk's driver `src/` slice.
class CourierVehicleDetailsAdapter implements CourierVehicleCapture {
  CourierRepositoryFacade get _repository {
    final getIt = GetIt.instance;
    if (!getIt.isRegistered<CourierRepositoryFacade>()) {
      DriverDeliveryDependencies.register(getIt);
    }
    return getIt.get<CourierRepositoryFacade>();
  }

  @override
  Future<void> submitVehicle({
    required String type,
    required String brand,
    required String model,
    required String number,
    required String color,
    required String height,
    required String width,
    required String length,
    required String weight,
    String? imagePath,
  }) async {
    // Best-effort by contract (the capture interface's rule): a failed
    // upload or create must never trap a freshly registered courier - the
    // profile page's edit-car modal offers the details again, so failures
    // are logged, not thrown.
    String? imageUrl;
    if (imagePath != null && imagePath.isNotEmpty) {
      final upload = await GetIt.instance
          .get<GalleryRepositoryFacade>()
          .uploadImage(imagePath, UploadType.users);
      // (UploadType.users: legacy deliveryCar type has no base_sdk member -
      // the Frappe gallery lands courier uploads on the User doctype.)
      upload.when(
        success: (data) => imageUrl = data.imageData?.title,
        failure: (failure, statusCode) => debugPrint(
            '==> vehicle image upload failed: $failure ($statusCode)'),
      );
    }
    final result = await _repository.createCarInfo(
      type: type,
      brand: brand,
      model: model,
      number: number,
      color: color,
      height: height,
      width: width,
      length: length,
      weight: weight,
      imageUrl: imageUrl,
    );
    result.when(
      success: (_) {},
      failure: (failure, statusCode) => debugPrint(
          '==> vehicle details create failed: $failure ($statusCode)'),
    );
  }
}
