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

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:percent_indicator/percent_indicator.dart';
import 'package:intl/intl.dart' as intl;

import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/helper/shimmer.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/marker_image_cropper.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:delivery_sdk/src/driver/application/push_order/push_order_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_helpers.dart';

class PushOrder extends ConsumerStatefulWidget {
  final OrderDetailData pushModel;
  final bool isActive;

  const PushOrder({super.key, required this.pushModel, required this.isActive});

  @override
  ConsumerState<PushOrder> createState() => _PushOrderState();
}

class _PushOrderState extends ConsumerState<PushOrder> {
  @override
  void initState() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(pushOrderProvider.notifier).startTimer();
    });
    super.initState();
  }

  @override
  void deactivate() {
    ref.read(pushOrderProvider.notifier).disposeTimer();
    super.deactivate();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(pushOrderProvider, (previous, next) {
      if (next.isTimeOut) {
        Navigator.pop(context);
      }
    });
    final notifier = ref.read(pushOrderProvider.notifier);

    return Container(
      height: widget.isActive ? 500.h : 400.h,
      width: double.infinity,
      color: AppStyle.transparent,
      child: Stack(
        children: [
          Positioned(
            bottom: 64.h,
            child: Container(
              height: widget.isActive ? 400.h : 300.h,
              width: MediaQuery.sizeOf(context).width - 32.w,
              decoration: BoxDecoration(
                color: AppStyle.white,
                borderRadius: BorderRadius.circular(10.r),
              ),
              child: Padding(
                padding: EdgeInsets.only(
                  top: widget.isActive ? 84.h : 32.h,
                  left: 16.w,
                  right: 16.w,
                ),
                child: Column(
                  children: [
                    _orderAvatar(),
                    const Spacer(),
                    const Divider(color: AppStyle.borderColor),
                    16.verticalSpace,
                    Row(
                      children: [
                        SvgPicture.asset("assets/svg/cutter.svg", width: 18.r),
                        10.horizontalSpace,
                        Text(
                          AppHelpers.numberFormat(
                            number: widget.pushModel.totalPrice ?? 0,
                          ),
                          style: AppStyle.interSemi(size: 12.sp),
                        ),
                        const Spacer(),
                        Icon(Remix.takeaway_fill, size: 18.sp),
                        10.horizontalSpace,
                        Text(
                          AppHelpers.numberFormat(
                            number: widget.pushModel.deliveryFee ?? 0,
                          ),
                          style: AppStyle.interSemi(size: 12.sp),
                        ),
                        const Spacer(),
                        Icon(Remix.bank_card_2_line, size: 18.sp),
                        10.horizontalSpace,
                        Text(
                          widget.pushModel.transaction?.paymentSystem?.tag ??
                              "",
                          style: AppStyle.interSemi(size: 12.sp),
                        ),
                      ],
                    ),
                    // COD: make the amount the driver must physically
                    // collect unmissable before accepting the push order.
                    if ((widget.pushModel.transaction?.paymentSystem?.tag ??
                                '')
                            .toLowerCase() ==
                        'cash') ...[
                      12.verticalSpace,
                      Row(
                        children: [
                          Icon(Remix.money_dollar_circle_fill,
                              size: 20.sp, color: AppStyle.primary),
                          10.horizontalSpace,
                          Expanded(
                            child: Text(
                              "${AppHelpers.getTranslation(TrKeys.cashToCollect)}: ${AppHelpers.numberFormat(number: widget.pushModel.totalPrice ?? 0)}",
                              style: AppStyle.interBold(
                                size: 14.sp,
                                color: AppStyle.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                    16.verticalSpace,
                    const Divider(color: AppStyle.borderColor),
                    const Spacer(),
                    Row(
                      children: [
                        Expanded(
                          child: CustomButton(
                            title: AppHelpers.getTranslation(TrKeys.skip),
                            onPressed: () {
                              Navigator.pop(context);
                            },
                            background: AppStyle.transparent,
                            borderColor: AppStyle.black,
                          ),
                        ),
                        14.horizontalSpace,
                        Expanded(
                          child: CustomButton(
                            isLoading: ref.watch(pushOrderProvider).isLoading,
                            title: widget.isActive
                                ? AppHelpers.getTranslation(TrKeys.accept)
                                : AppHelpers.getTranslation(
                                    TrKeys.orderInformation,
                                  ),
                            onPressed: () async {
                              if (widget.isActive) {
                                final ImageCropperForMarker image =
                                    ImageCropperForMarker();
                                notifier.changeLoading();
                                ref
                                    .read(homeProvider.notifier)
                                    .goMarket(
                                      context: context,
                                      orderId: widget.pushModel.id,
                                      order: widget.pushModel,
                                      setOrder: true,
                                      onSuccess: () async {
                                        notifier.changeLoading();
                                        Navigator.pop(context);
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
                                                double.parse(
                                                  widget
                                                          .pushModel
                                                          .shop
                                                          ?.location
                                                          ?.latitude ??
                                                      "0",
                                                ),
                                                double.parse(
                                                  widget
                                                          .pushModel
                                                          .shop
                                                          ?.location
                                                          ?.longitude ??
                                                      "0",
                                                ),
                                              ),
                                              market: Marker(
                                                markerId: const MarkerId(
                                                  "Shop",
                                                ),
                                                position: LatLng(
                                                  double.parse(
                                                    widget
                                                            .pushModel
                                                            .shop
                                                            ?.location
                                                            ?.latitude ??
                                                        "0",
                                                  ),
                                                  double.parse(
                                                    widget
                                                            .pushModel
                                                            .shop
                                                            ?.location
                                                            ?.longitude ??
                                                        "0",
                                                  ),
                                                ),
                                                icon: await image
                                                    .resizeAndCircle(
                                                      widget
                                                              .pushModel
                                                              .shop
                                                              ?.logoImg ??
                                                          "",
                                                      120,
                                                    ),
                                              ),
                                            );
                                      },
                                    );
                              } else {
                                Navigator.pop(context);
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                    24.verticalSpace,
                  ],
                ),
              ),
            ),
          ),
          widget.isActive ? _timer(context) : const SizedBox.shrink(),
        ],
      ),
    );
  }

  Widget _timer(BuildContext context) {
    return Positioned(
      top: 0,
      right: (MediaQuery.sizeOf(context).width - 32.w) / 2 - 52.r,
      child: Container(
        padding: EdgeInsets.all(4.r),
        decoration: const BoxDecoration(
          color: AppStyle.white,
          shape: BoxShape.circle,
        ),
        child: CircularPercentIndicator(
          radius: 48.r,
          lineWidth: 12.r,
          percent:
              double.parse(
                ref
                    .watch(pushOrderProvider)
                    .timerText
                    .substring(
                      0,
                      ref.watch(pushOrderProvider).timerText.indexOf(' '),
                    ),
              ) /
              CourierHelpers.getAppDeliveryTime(),
          center: Text(
            ref.watch(pushOrderProvider).timerText,
            style: AppStyle.interSemi(size: 18.sp),
          ),
          fillColor: AppStyle.transparent,
          backgroundColor: AppStyle.shimmerBase,
          progressColor: Color(0xFFF26110),
          circularStrokeCap: CircularStrokeCap.round,
        ),
      ),
    );
  }

  Widget _orderAvatar() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 32.r,
              width: 32.r,
              decoration: const BoxDecoration(
                color: AppStyle.white,
                shape: BoxShape.circle,
              ),
              child: ClipOval(
                child: CachedNetworkImage(
                  imageUrl: "${widget.pushModel.shop?.logoImg}",
                  fit: BoxFit.cover,
                  progressIndicatorBuilder: (context, url, progress) {
                    return ImageShimmer(isCircle: true, size: 32.r);
                  },
                  errorWidget: (context, url, error) {
                    return Container(
                      height: 32.r,
                      width: 32.r,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppStyle.bgGrey,
                      ),
                      alignment: Alignment.center,
                      child: const Icon(
                        Remix.image_line,
                        color: AppStyle.black,
                      ),
                    );
                  },
                ),
              ),
            ),
            16.horizontalSpace,
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.pushModel.shop?.translation?.title ?? "",
                  style: AppStyle.interSemi(size: 14.sp, letterSpacing: -0.3),
                ),
                2.verticalSpace,
                IntrinsicHeight(
                  child: Row(
                    children: [
                      Text(
                        '№ ${widget.pushModel.id}',
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                      const VerticalDivider(),
                      Text(
                        intl.DateFormat("hh:mm").format(
                          DateTime.tryParse(
                                widget.pushModel.updatedAt ??
                                    DateTime.now().toString(),
                              )?.toLocal() ??
                              DateTime.now(),
                        ),
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                      16.horizontalSpace,
                      Icon(Remix.building_fill, size: 18.r),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
        Padding(
          padding: EdgeInsets.only(left: 14.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 4.r,
                height: 4.r,
                margin: EdgeInsets.only(bottom: 6.h, top: 6.h),
                decoration: const BoxDecoration(
                  color: AppStyle.tabBarBorderColor,
                  shape: BoxShape.circle,
                ),
              ),
              Container(
                width: 4.r,
                height: 4.r,
                margin: EdgeInsets.only(bottom: 10.h),
                decoration: const BoxDecoration(
                  color: AppStyle.tabBarBorderColor,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 32.r,
              width: 32.r,
              decoration: const BoxDecoration(
                color: AppStyle.white,
                shape: BoxShape.circle,
              ),
              child: ClipOval(
                child: CachedNetworkImage(
                  imageUrl: widget.pushModel.user?.img ?? "",
                  fit: BoxFit.cover,
                  progressIndicatorBuilder: (context, url, progress) {
                    return ImageShimmer(isCircle: true, size: 32.r);
                  },
                  errorWidget: (context, url, error) {
                    return Container(
                      height: 32.r,
                      width: 32.r,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppStyle.bgGrey,
                      ),
                      alignment: Alignment.center,
                      child: const Icon(
                        Remix.image_line,
                        color: AppStyle.black,
                      ),
                    );
                  },
                ),
              ),
            ),
            16.horizontalSpace,
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 100.w,
                  child: Text(
                    widget.pushModel.address?.address ?? "",
                    style: AppStyle.interSemi(size: 14.sp, letterSpacing: -0.3),
                    maxLines: 1,
                  ),
                ),
                2.verticalSpace,
                IntrinsicHeight(
                  child: Row(
                    children: [
                      Text(
                        widget.pushModel.user == null
                            ? AppHelpers.getTranslation(TrKeys.deletedUser)
                            : widget.pushModel.user?.firstname ?? "",
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                      const VerticalDivider(),
                      Text(
                        widget.pushModel.user?.phone ?? "",
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
