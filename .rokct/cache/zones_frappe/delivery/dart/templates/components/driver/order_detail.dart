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

// ignore_for_file: use_build_context_synchronously

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:${package}/presentation/pages/home/widgets/foods_page.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'image_dialog.dart';
import 'order_item.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/marker_image_cropper.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';

class OrderDetail extends StatelessWidget {
  final OrderDetailData order;
  final bool isOrder;
  final bool isActiveButton;

  const OrderDetail({
    super.key,
    this.isOrder = false,
    required this.order,
    this.isActiveButton = false,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 10.h),
      shrinkWrap: true,
      children: [
        OrderItem(order: order, isSetCurrentOrder: isOrder && isActiveButton),
        isOrder
            ? Column(
                children: [
                  16.verticalSpace,
                  CustomButton(
                    title: AppHelpers.getTranslation(TrKeys.orderInformation),
                    onPressed: () {
                      AppHelpers.showCustomModalBottomSheet(
                        context: context,
                        modal: FoodsPage(order: order),
                        isDarkMode: false,
                      );
                    },
                    background: AppStyle.transparent,
                    borderColor: AppStyle.black,
                  ),
                  16.verticalSpace,
                  Consumer(
                    builder: (context, ref, child) {
                      return CustomButton(
                        isLoading: ref.watch(homeProvider).isLoading,
                        title: AppHelpers.getTranslation(
                          isOrder
                              ? (order.status != "on_a_way"
                                    ? TrKeys.startShopping
                                    : TrKeys.completeCheckout)
                              : TrKeys.order,
                        ),
                        onPressed: () async {
                          if (order.deliveryman == null) {
                            final ImageCropperForMarker image =
                                ImageCropperForMarker();
                            ref
                                .read(homeProvider.notifier)
                                .goMarket(
                                  context: context,
                                  orderId: order.id,
                                  setOrder: !isActiveButton && true,
                                  order: order,
                                  onSuccess: () async {
                                    ref
                                        .read(homeProvider.notifier)
                                        .getRoutingAll(
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
                                            double.parse(
                                              order.shop?.location?.latitude ??
                                                  "0",
                                            ),
                                            double.parse(
                                              order.shop?.location?.longitude ??
                                                  "0",
                                            ),
                                          ),
                                          market: Marker(
                                            markerId: const MarkerId("Shop"),
                                            position: LatLng(
                                              double.parse(
                                                order
                                                        .shop
                                                        ?.location
                                                        ?.latitude ??
                                                    "41.285127",
                                              ),
                                              double.parse(
                                                order
                                                        .shop
                                                        ?.location
                                                        ?.longitude ??
                                                    "69.172530",
                                              ),
                                            ),
                                            icon: await image.resizeAndCircle(
                                              order.shop?.logoImg ?? "",
                                              120,
                                            ),
                                          ),
                                        );
                                    context.router.popUntilRoot();
                                  },
                                );
                          } else {
                            final ImageCropperForMarker image =
                                ImageCropperForMarker();
                            if (order.status != "on_a_way") {
                              ref
                                  .read(homeProvider.notifier)
                                  .getRoutingAll(
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
                                      double.parse(
                                        order.shop?.location?.latitude ??
                                            "41.285127",
                                      ),
                                      double.parse(
                                        order.shop?.location?.longitude ??
                                            "69.172530",
                                      ),
                                    ),
                                    market: Marker(
                                      markerId: const MarkerId("Shop"),
                                      position: LatLng(
                                        double.parse(
                                          order.shop?.location?.latitude ??
                                              "41.285127",
                                        ),
                                        double.parse(
                                          order.shop?.location?.longitude ??
                                              "69.172530",
                                        ),
                                      ),
                                      icon: await image.resizeAndCircle(
                                        order.shop?.logoImg ?? "",
                                        120,
                                      ),
                                    ),
                                  );
                            } else {
                              ref
                                  .read(homeProvider.notifier)
                                  .getRoutingAll(
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
                                      double.parse(
                                        order.location?.latitude ?? "41.285127",
                                      ),
                                      double.parse(
                                        order.location?.longitude ??
                                            "69.172530",
                                      ),
                                    ),
                                    market: Marker(
                                      markerId: const MarkerId("User"),
                                      position: LatLng(
                                        double.parse(
                                          order.location?.latitude ??
                                              "41.285127",
                                        ),
                                        double.parse(
                                          order.location?.longitude ??
                                              "69.172530",
                                        ),
                                      ),
                                      icon: await image.resizeAndCircle(
                                        order.user?.img ?? "",
                                        120,
                                      ),
                                    ),
                                  );
                            }
                            order.status != "on_a_way"
                                ? ref
                                      .read(homeProvider.notifier)
                                      .goMarket(
                                        context: context,
                                        orderId: "",
                                        order: order,
                                        setOrder: !isActiveButton,
                                        onSuccess: () {},
                                      )
                                : ref
                                      .read(homeProvider.notifier)
                                      .goClient(
                                        context,
                                        order.id,
                                        order: order,
                                      );
                            Navigator.pop(context);
                            Navigator.pop(context);
                          }
                        },
                      );
                    },
                  ),
                  16.verticalSpace,
                ],
              )
            : Column(
                children: [
                  16.verticalSpace,
                  if (order.afterDeliveredImage != null)
                    GestureDetector(
                      onTap: () {
                        AppHelpers.showAlertDialog(
                          context: context,
                          child: ImageDialog(img: order.afterDeliveredImage),
                        );
                      },
                      child: Container(
                        margin: EdgeInsets.only(top: 8.h),
                        decoration: BoxDecoration(
                          color: AppStyle.transparent,
                          border: Border.all(color: AppStyle.black),
                          borderRadius: BorderRadius.circular(10.r),
                        ),
                        padding: REdgeInsets.all(16),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              AppHelpers.getTranslation(TrKeys.orderImage),
                              style: AppStyle.interNormal(
                                size: 14.sp,
                                color: AppStyle.blackColor,
                                letterSpacing: -0.3,
                              ),
                            ),
                            12.horizontalSpace,
                            const Icon(Remix.gallery_fill),
                          ],
                        ),
                      ),
                    ),
                  16.verticalSpace,
                ],
              ),
      ],
    );
  }
}
