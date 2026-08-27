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

import 'package:flutter/material.dart';
import 'package:auto_route/auto_route.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
// The manager zone slice lives in zones_sdk's own src/manager/ role folder
// (ported from paas_manager's application/restaurant/delivery_zone/ in the
// 2026-08 refork). Deep import rather than the zones_sdk.dart barrel: the
// barrel is common-only because the composer strips the other role's
// lib/src/<role>/ folder from every host's cache, and this page only exists
// in manager hosts, where src/manager/ survives.
import 'package:zones_sdk/src/manager/application/delivery_zone/delivery_zone_provider.dart';

import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/constants/app_constants.dart';

@RoutePage(name: 'ManagerDeliveryZoneRoute')
class ManagerDeliveryZonePage extends ConsumerStatefulWidget {
  const ManagerDeliveryZonePage({super.key});

  @override
  ConsumerState<ManagerDeliveryZonePage> createState() =>
      _DeliveryZonePageState();
}

class _DeliveryZonePageState extends ConsumerState<ManagerDeliveryZonePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(deliveryZoneProvider.notifier).fetchDeliveryZone(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppStyle.textGrey,
      resizeToAvoidBottomInset: false,
      body: Consumer(
        builder: (context, ref, child) {
          final state = ref.watch(deliveryZoneProvider);
          final event = ref.read(deliveryZoneProvider.notifier);
          return Stack(
            children: [
              state.isLoading
                  ? Container(
                      width: double.infinity,
                      height: double.infinity,
                      color: AppStyle.white,
                    )
                  : GoogleMap(
                      tiltGesturesEnabled: false,
                      myLocationButtonEnabled: false,
                      zoomControlsEnabled: false,
                      polygons: state.polygon,
                      onTap: event.addTappedPoint,
                      initialCameraPosition: CameraPosition(
                        bearing: 0,
                        target: LatLng(
                          state.polygon.isNotEmpty
                              ? state.polygon.first.points.first.latitude
                              : AppHelpers.getInitialLatitude() ??
                                    AppConstants.demoLatitude,
                          state.polygon.isNotEmpty
                              ? state.polygon.first.points.first.longitude
                              : AppHelpers.getInitialLongitude() ??
                                    AppConstants.demoLongitude,
                        ),
                        tilt: 0,
                        zoom: 11,
                      ),
                    ),
              AnimatedPositioned(
                duration: const Duration(milliseconds: 150),
                bottom: 20.r,
                left: 15.r,
                right: 15.r,
                child: Row(
                  children: [
                    const PopButton(),
                    8.horizontalSpace,
                    if (state.tappedPoints.length > 3)
                      Expanded(
                        child: CustomButton(
                          title: AppHelpers.getTranslation(TrKeys.save),
                          isLoading: state.isSaving,
                          onPressed: () => event.updateDeliveryZone(
                            updateSuccess: context.router.maybePop,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
