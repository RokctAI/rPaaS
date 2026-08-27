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
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:map_launcher/map_launcher.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:base_sdk/src/models/data/parcel_order.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/marker_image_cropper.dart';
import 'package:${package}/presentation/component/maps_list.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:intl/intl.dart' as intl;
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';

class ParcelOrderPage extends StatelessWidget {
  final ParcelOrder? parcel;
  final bool isOrder;
  final bool isSet;

  const ParcelOrderPage({
    super.key,
    required this.parcel,
    required this.isOrder,
    required this.isSet,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 10.h),
      shrinkWrap: true,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                16.horizontalSpace,
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: MediaQuery.sizeOf(context).width - 180.w,
                      child: Text(
                        parcel?.addressFrom?.address ?? "",
                        style: AppStyle.interSemi(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ),
                    2.verticalSpace,
                    IntrinsicHeight(
                      child: Row(
                        children: [
                          Text(
                            "№ ${parcel?.id}",
                            style: AppStyle.interNormal(
                              size: 14.sp,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const VerticalDivider(),
                          Text(
                            intl.DateFormat(
                              "hh:mm",
                            ).format(parcel?.updatedAt ?? DateTime.now()),
                            style: AppStyle.interNormal(
                              size: 14.sp,
                              letterSpacing: -0.3,
                            ),
                          ),
                          16.horizontalSpace,
                          Icon(Remix.building_fill, size: 18.r),
                          IconButton(
                            padding: EdgeInsets.symmetric(horizontal: 6.w),
                            onPressed: () async {
                              AppHelpers.showCustomModalBottomSheet(
                                context: context,
                                modal: MapsList(
                                  location: Coords(
                                    parcel?.addressFrom?.latitude ?? 0,
                                    parcel?.addressFrom?.longitude ?? 0,
                                  ),
                                  title: "A",
                                ),
                                isDarkMode: false,
                              );
                            },
                            icon: Icon(Remix.map_2_fill, size: 18.r),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Row(
                  children: [
                    GestureDetector(
                      onTap: () async {
                        final Uri launchUri = Uri(
                          scheme: 'tel',
                          path: parcel?.phoneFrom ?? "",
                        );
                        await launchUrl(launchUri);
                      },
                      child: Container(
                        height: 38.r,
                        width: 38.r,
                        decoration: const BoxDecoration(
                          color: AppStyle.black,
                          shape: BoxShape.circle,
                        ),
                        margin: EdgeInsets.all(4.r),
                        child: Icon(
                          Remix.phone_fill,
                          color: AppStyle.white,
                          size: 20.r,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: () async {
                        final Uri launchUri = Uri(
                          scheme: 'sms',
                          path: parcel?.phoneFrom ?? "",
                        );
                        await launchUrl(launchUri);
                      },
                      child: Container(
                        height: 38.r,
                        width: 38.r,
                        decoration: const BoxDecoration(
                          color: AppStyle.black,
                          shape: BoxShape.circle,
                        ),
                        margin: EdgeInsets.all(4.r),
                        child: Icon(
                          Remix.chat_1_fill,
                          color: AppStyle.white,
                          size: 20.r,
                        ),
                      ),
                    ),
                  ],
                ),
                // Consumer(builder: (context, ref, child) {
                //         return CustomToggle(
                //           isOrder: true,
                //           isOnline: order.current ?? false,
                //           onChange: (bool value) {
                //             if (value) {
                //               ref
                //                   .read(orderProvider.notifier)
                //                   .setCurrentOrder(context, order.id ?? 0, () {
                //                 ref
                //                     .read(homeProvider.notifier)
                //                     .fetchCurrentOrder(context);
                //               });
                //             }
                //           },
                //         );
                //       })
              ],
            ),
            24.verticalSpace,
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                16.horizontalSpace,
                SizedBox(
                  width: MediaQuery.sizeOf(context).width - 180.w,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: MediaQuery.sizeOf(context).width - 190.w,
                        child: Text(
                          parcel?.addressTo?.address ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            letterSpacing: -0.3,
                          ),
                          maxLines: 1,
                        ),
                      ),
                      2.verticalSpace,
                      IntrinsicHeight(
                        child: Row(
                          children: [
                            Expanded(
                              child: Text(
                                parcel?.usernameTo ?? "",
                                style: AppStyle.interNormal(
                                  size: 12.sp,
                                  letterSpacing: -0.3,
                                ),
                              ),
                            ),
                            const VerticalDivider(),
                            Text(
                              parcel?.phoneTo ?? "",
                              style: AppStyle.interNormal(
                                size: 12.sp,
                                letterSpacing: -0.3,
                              ),
                            ),
                            IconButton(
                              padding: EdgeInsets.symmetric(horizontal: 6.w),
                              onPressed: () {
                                AppHelpers.showCustomModalBottomSheet(
                                  context: context,
                                  modal: MapsList(
                                    location: Coords(
                                      parcel?.addressTo?.latitude ?? 0,
                                      parcel?.addressTo?.longitude ?? 0,
                                    ),
                                    title: "B",
                                  ),
                                  isDarkMode: false,
                                );
                              },
                              icon: Icon(Remix.map_2_fill, size: 18.r),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                Row(
                  children: [
                    GestureDetector(
                      onTap: () async {
                        final Uri launchUri = Uri(
                          scheme: 'tel',
                          path: parcel?.phoneTo ?? "",
                        );
                        await launchUrl(launchUri);
                      },
                      child: Container(
                        height: 38.r,
                        width: 38.r,
                        decoration: const BoxDecoration(
                          color: AppStyle.black,
                          shape: BoxShape.circle,
                        ),
                        margin: EdgeInsets.all(4.r),
                        child: Icon(
                          Remix.phone_fill,
                          color: AppStyle.white,
                          size: 20.r,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: () async {
                        final Uri launchUri = Uri(
                          scheme: 'sms',
                          path: parcel?.phoneTo ?? "",
                        );
                        await launchUrl(launchUri);
                      },
                      child: Container(
                        height: 38.r,
                        width: 38.r,
                        decoration: const BoxDecoration(
                          color: AppStyle.black,
                          shape: BoxShape.circle,
                        ),
                        margin: EdgeInsets.all(4.r),
                        child: Icon(
                          Remix.chat_1_fill,
                          color: AppStyle.white,
                          size: 20.r,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
        isOrder
            ? Column(
                children: [
                  32.verticalSpace,
                  Consumer(
                    builder: (context, ref, child) {
                      return CustomButton(
                        isLoading: ref.watch(homeProvider).isLoading,
                        title: AppHelpers.getTranslation(TrKeys.order),
                        onPressed: () async {
                          if (parcel?.deliveryman == null) {
                            final ImageCropperForMarker image =
                                ImageCropperForMarker();
                            ref
                                .read(homeProvider.notifier)
                                .goMarketParcel(
                                  context: context,
                                  parcelId: parcel?.id,
                                  setOrder: isSet,
                                  parcel: parcel,
                                );
                            ref
                                .read(homeProvider.notifier)
                                .getRoutingAll(
                                  // ignore: use_build_context_synchronously
                                  context: context,
                                  start: LatLng(
                                    LocalStorage.getAddressSelected()
                                            ?.latitude ??
                                        AppConstants.demoLatitude,
                                    LocalStorage.getAddressSelected()
                                            ?.longitude ??
                                        AppConstants.demoLongitude,
                                  ),
                                  end: LatLng(
                                    parcel?.addressFrom?.latitude ?? 0,
                                    parcel?.addressFrom?.longitude ?? 0,
                                  ),
                                  market: Marker(
                                    markerId: const MarkerId("Shop"),
                                    position: LatLng(
                                      parcel?.addressFrom?.latitude ?? 0,
                                      parcel?.addressFrom?.longitude ?? 0,
                                    ),
                                    icon: await image.resizeAndCircle("", 120),
                                  ),
                                );
                            if (context.mounted) {
                              context.router.popUntilRoot();
                            }
                          } else {
                            final ImageCropperForMarker image =
                                ImageCropperForMarker();

                            if (parcel?.status != "on_a_way") {
                              ref
                                  .read(homeProvider.notifier)
                                  .goMarketParcel(
                                    context: context,
                                    parcelId: "",
                                    parcel: parcel,
                                    setOrder: isSet,
                                  );
                              ref
                                  .read(homeProvider.notifier)
                                  .getRoutingAll(
                                    // ignore: use_build_context_synchronously
                                    context: context,
                                    start: LatLng(
                                      LocalStorage.getAddressSelected()
                                              ?.latitude ??
                                          AppConstants.demoLatitude,
                                      LocalStorage.getAddressSelected()
                                              ?.longitude ??
                                          AppConstants.demoLongitude,
                                    ),
                                    end: LatLng(
                                      parcel?.addressFrom?.latitude ?? 0,
                                      parcel?.addressFrom?.longitude ?? 0,
                                    ),
                                    market: Marker(
                                      markerId: const MarkerId("User"),
                                      position: LatLng(
                                        parcel?.addressFrom?.latitude ?? 0,
                                        parcel?.addressFrom?.longitude ?? 0,
                                      ),
                                      icon: await image.resizeAndCircle(
                                        "",
                                        120,
                                      ),
                                    ),
                                  );
                            } else {
                              ref
                                  .read(homeProvider.notifier)
                                  .goClientParcel(
                                    context,
                                    parcel?.id,
                                    parcel: parcel,
                                  );
                              ref
                                  .read(homeProvider.notifier)
                                  .getRoutingAll(
                                    // ignore: use_build_context_synchronously
                                    context: context,
                                    start: LatLng(
                                      LocalStorage.getAddressSelected()
                                              ?.latitude ??
                                          AppConstants.demoLatitude,
                                      LocalStorage.getAddressSelected()
                                              ?.longitude ??
                                          AppConstants.demoLongitude,
                                    ),
                                    end: LatLng(
                                      parcel?.addressTo?.latitude ?? 0,
                                      parcel?.addressTo?.longitude ?? 0,
                                    ),
                                    market: Marker(
                                      markerId: const MarkerId("User"),
                                      position: LatLng(
                                        parcel?.addressTo?.latitude ?? 0,
                                        parcel?.addressTo?.longitude ?? 0,
                                      ),
                                      icon: await image.resizeAndCircle(
                                        "",
                                        120,
                                      ),
                                    ),
                                  );
                            }
                            if (context.mounted) {
                              Navigator.pop(context);
                              Navigator.pop(context);
                            }
                          }
                        },
                      );
                    },
                  ),
                  16.verticalSpace,
                ],
              )
            : const SizedBox.shrink(),
      ],
    );
  }
}
