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
import 'package:map_launcher/map_launcher.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:delivery_sdk/src/driver/application/order/order_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:${package}/presentation/component/maps_list.dart';

import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:intl/intl.dart' as intl;
import 'package:base_sdk/src/presentation/components/helper/shimmer.dart';
import 'custom_toggle.dart';
import 'maps_list.dart';

class OrderItem extends StatelessWidget {
  final OrderDetailData order;
  final bool isDeliveryShop;
  final bool isDeliveryClient;
  final bool isSetCurrentOrder;

  const OrderItem({
    super.key,
    required this.order,
    this.isDeliveryShop = false,
    this.isDeliveryClient = false,
    this.isSetCurrentOrder = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _orderAvatar(context),
        // 18+ order: the courier must check the recipient's ID at the
        // door. Surfaced up front - this component renders on the order
        // card AND in the delivery bottom sheet - so the courier knows
        // an ID check is required BEFORE arriving at the customer.
        if (order.containsAdultItems ?? false) ...[
          16.verticalSpace,
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16.r),
            decoration: BoxDecoration(
              color: AppStyle.white,
              borderRadius: BorderRadius.circular(10.r),
              border: Border.all(color: AppStyle.red),
            ),
            child: Row(
              children: [
                Icon(
                  Remix.error_warning_fill,
                  size: 20.sp,
                  color: AppStyle.red,
                ),
                10.horizontalSpace,
                Expanded(
                  child: Text(
                    AppHelpers.getTranslation(TrKeys.idRequired18Plus),
                    style: AppStyle.interBold(
                      size: 14.sp,
                      color: AppStyle.red,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        16.verticalSpace,
        Container(
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(10.r),
          ),
          padding: EdgeInsets.all(16.r),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    AppHelpers.getTranslation(TrKeys.restaurantHome),
                    style: AppStyle.interNormal(
                      size: 12.sp,
                      color: AppStyle.black,
                      letterSpacing: -0.3,
                    ),
                  ),
                  Text(
                    "${(order.distance ?? 0).toString()} ${AppHelpers.getTranslation(TrKeys.km)}",
                    style: AppStyle.interSemi(
                      size: 14.sp,
                      color: AppStyle.black,
                      letterSpacing: -0.3,
                    ),
                  ),
                ],
              ),
              order.address?.house != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.home),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.house ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
              order.address?.office != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.entr),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.office ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
              order.address?.floor != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.apart),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.floor ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
            ],
          ),
        ),
        10.verticalSpace,
        Container(
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(10.r),
          ),
          padding: EdgeInsets.all(16.r),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    AppHelpers.getTranslation(TrKeys.askThisCodeFromCustomer),
                    style: AppStyle.interNormal(
                      size: 12.sp,
                      color: AppStyle.black,
                      letterSpacing: -0.3,
                    ),
                  ),
                  Text(
                    (order.otp ?? 0).toString(),
                    style: AppStyle.interSemi(
                      size: 14.sp,
                      color: AppStyle.black,
                      letterSpacing: -0.3,
                    ),
                  ),
                ],
              ),
              order.address?.house != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.home),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.house ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
              order.address?.office != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.entr),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.office ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
              order.address?.floor != "null"
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.apart),
                          style: AppStyle.interNormal(
                            size: 12.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                        Text(
                          order.address?.floor ?? "",
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.black,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
            ],
          ),
        ),
        10.verticalSpace,
        order.note != null ? _reminder() : const SizedBox.shrink(),
        10.verticalSpace,
        Container(
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(10.r),
          ),
          padding: EdgeInsets.all(16.r),
          child: Column(
            children: [
              Row(
                children: [
                  SvgPicture.asset("assets/svg/cutter.svg", width: 18.r),
                  10.horizontalSpace,
                  Text(
                    AppHelpers.numberFormat(number: order.totalPrice ?? 0),
                    style: AppStyle.interSemi(size: 12.sp),
                  ),
                  const Spacer(),
                  Icon(Remix.takeaway_fill, size: 18.sp),
                  10.horizontalSpace,
                  Text(
                    AppHelpers.numberFormat(number: order.deliveryFee ?? 0),
                    style: AppStyle.interSemi(size: 12.sp),
                  ),
                  const Spacer(),
                  Icon(Remix.bank_card_2_line, size: 18.sp),
                  10.horizontalSpace,
                  Text(
                    order.transaction?.paymentSystem?.tag ?? "",
                    style: AppStyle.interSemi(size: 12.sp),
                  ),
                ],
              ),
              // COD: make the amount the driver must physically collect
              // unmissable.
              if ((order.transaction?.paymentSystem?.tag ?? '')
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
                        "${AppHelpers.getTranslation(TrKeys.cashToCollect)}: ${AppHelpers.numberFormat(number: order.totalPrice ?? 0)}",
                        style: AppStyle.interBold(
                          size: 14.sp,
                          color: AppStyle.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _orderAvatar(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
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
                  imageUrl: "${order.shop?.logoImg}",
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
                  order.shop?.translation?.title ?? "",
                  style: AppStyle.interSemi(size: 14.sp, letterSpacing: -0.3),
                ),
                2.verticalSpace,
                IntrinsicHeight(
                  child: Row(
                    children: [
                      Text(
                        "№ ${order.id}",
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          letterSpacing: -0.3,
                        ),
                      ),
                      const VerticalDivider(),
                      Text(
                        intl.DateFormat("hh:mm").format(
                          DateTime.tryParse(
                                order.updatedAt ?? DateTime.now().toString(),
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
                      IconButton(
                        padding: EdgeInsets.symmetric(horizontal: 6.w),
                        onPressed: () async {
                          AppHelpers.showCustomModalBottomSheet(
                            context: context,
                            modal: MapsList(
                              location: Coords(
                                double.tryParse(
                                      order.shop?.location?.latitude ?? "0",
                                    ) ??
                                    0,
                                double.tryParse(
                                      order.shop?.location?.longitude ?? "0",
                                    ) ??
                                    0,
                              ),
                              title: "Shop",
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
            isDeliveryShop
                ? Row(
                    children: [
                      GestureDetector(
                        onTap: () async {
                          final Uri launchUri = Uri(
                            scheme: 'tel',
                            path: order.shop?.phone ?? "",
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
                            path: order.shop?.phone ?? "",
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
                  )
                : const SizedBox.shrink(),
            isSetCurrentOrder
                ? Consumer(
                    builder: (context, ref, child) {
                      return CustomToggle(
                        isOrder: true,
                        isOnline: order.current ?? false,
                        onChange: (bool value) {
                          if (value && order.id != null) {
                            ref.read(orderProvider.notifier).setCurrentOrder(
                              context,
                              order.id!,
                              () {
                                ref
                                    .read(homeProvider.notifier)
                                    .fetchCurrentOrder(context);
                              },
                            );
                          }
                        },
                      );
                    },
                  )
                : const SizedBox.shrink(),
          ],
        ),
        Padding(
          padding: EdgeInsets.only(left: 14.sp),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 4.r,
                height: 4.r,
                margin: EdgeInsets.only(bottom: 6.h),
                decoration: const BoxDecoration(
                  color: AppStyle.orderStatusProgressBack,
                  shape: BoxShape.circle,
                ),
              ),
              Container(
                width: 4.r,
                height: 4.r,
                margin: EdgeInsets.only(bottom: 4.h),
                decoration: const BoxDecoration(
                  color: AppStyle.orderStatusProgressBack,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
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
                  imageUrl: "${order.user?.img}",
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
            SizedBox(
              width: MediaQuery.sizeOf(context).width - 180.w,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: MediaQuery.sizeOf(context).width - 190.w,
                    child: Text(
                      order.address?.address ?? "",
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
                            order.user == null
                                ? AppHelpers.getTranslation(TrKeys.deletedUser)
                                : order.user?.firstname ?? "",
                            style: AppStyle.interNormal(
                              size: 12.sp,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ),
                        const VerticalDivider(),
                        Text(
                          order.user?.phone ?? "",
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
                                  double.tryParse(
                                        order.location?.latitude ?? "0",
                                      ) ??
                                      0,
                                  double.tryParse(
                                        order.location?.longitude ?? "0",
                                      ) ??
                                      0,
                                ),
                                title: "User",
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
            isDeliveryClient
                ? Row(
                    children: [
                      GestureDetector(
                        onTap: () async {
                          final Uri launchUri = Uri(
                            scheme: 'tel',
                            path: order.user?.phone ?? "",
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
                            path: order.user?.phone ?? "",
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
                  )
                : const SizedBox.shrink(),
          ],
        ),
      ],
    );
  }

  Widget _reminder() {
    return Container(
      decoration: BoxDecoration(
        color: AppStyle.white,
        borderRadius: BorderRadius.circular(10.r),
      ),
      padding: EdgeInsets.symmetric(vertical: 12.h, horizontal: 16.w),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Icon(Remix.chat_1_fill),
          12.horizontalSpace,
          Expanded(
            child: Text(
              order.note ?? "",
              style: AppStyle.interRegular(size: 13.sp, color: AppStyle.black),
            ),
          ),
        ],
      ),
    );
  }
}
