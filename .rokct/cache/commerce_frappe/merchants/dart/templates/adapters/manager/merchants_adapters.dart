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
import 'package:base_sdk/src/handlers/api_result.dart';
import 'package:merchants_sdk/src/manager/di/manager_merchants_di.dart';
import 'package:merchants_sdk/src/manager/domain/interface/seller_shop.dart';
import 'package:merchants_sdk/src/manager/presentation/widgets/shop_setup_slide.dart';

/// Host-side wiring for merchants_sdk's manager registration seam (ADR-005,
/// the orders_sdk `orders_adapters.dart` / lms `LmsSchoolCaptureAdapter`
/// precedent).
///
/// merchants_sdk owns the shop-setup step widget ([ShopSetupSlide]) that its
/// manifest `registration_steps` entry injects into auth_sdk's post-register
/// pipeline, and declares [SellerShopSetupCapture] in its own terms; this
/// installed host-composition file supplies the adapter that lands the
/// capture on [SellerShopRepositoryFacade.createShop] (`shop.create_shop`).
/// This file lives in templates/ and installs into the app at compose time
/// (manager flavour only, see manifest.json app_type.manager), which is why
/// it may reach into merchants_sdk's manager `src/` slice.
class MerchantsShopSetupAdapter implements SellerShopSetupCapture {
  SellerShopRepositoryFacade get _repository {
    final getIt = GetIt.instance;
    if (!getIt.isRegistered<SellerShopRepositoryFacade>()) {
      ManagerMerchantsDependencies.register(getIt);
    }
    return getIt.get<SellerShopRepositoryFacade>();
  }

  @override
  Future<void> submitShop({
    required String name,
    String? phone,
    String? address,
  }) async {
    // Best-effort by contract (the capture interface's rule): a failed
    // create must never trap a freshly registered seller — the restaurant
    // tab handles the no-shop state, so the failure is logged, not thrown.
    final result = await _repository.createShop(
      name: name,
      phone: phone,
      address: address,
    );
    result.when(
      success: (_) {},
      failure: (failure, statusCode) => debugPrint(
          '==> shop setup create failed: $failure ($statusCode)'),
    );
  }
}
