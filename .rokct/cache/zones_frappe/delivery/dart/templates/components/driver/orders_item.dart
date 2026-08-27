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

import 'package:auto_size_text/auto_size_text.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:base_sdk/src/presentation/components/helper/shimmer.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:intl/intl.dart' as intl;

import 'order_detail.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class OrdersItem extends StatelessWidget {
  final OrderDetailData order;
  final bool isOrder;
  final bool isActiveButton;

  const OrdersItem({
    super.key,
    required this.order,
    required this.isOrder,
    this.isActiveButton = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () async {
        AppHelpers.showCustomModalBottomSheet(
          paddingTop: MediaQuery.paddingOf(context).top,
          context: context,
          radius: 12,
          modal: OrderDetail(
            isOrder: isOrder,
            order: order,
            isActiveButton: isActiveButton,
          ),
          isDarkMode: true,
        );
      },
      child: Container(
        width: double.infinity,
        margin: EdgeInsets.only(bottom: 10.h),
        padding: EdgeInsets.symmetric(vertical: 16.h),
        decoration: BoxDecoration(
          color: AppStyle.white,
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          children: [
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.w),
              child: Column(
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
                            style: AppStyle.interSemi(
                              size: 14.sp,
                              letterSpacing: -0.3,
                            ),
                          ),
                          2.verticalSpace,
                          IntrinsicHeight(
                            child: Row(
                              children: [
                                Text(
                                  '№ ${order.id}',
                                  style: AppStyle.interNormal(
                                    size: 14.sp,
                                    letterSpacing: -0.3,
                                  ),
                                ),
                                const VerticalDivider(),
                                Text(
                                  intl.DateFormat("MMM dd hh:mm").format(
                                    DateTime.parse(
                                      order.createdAt ??
                                          DateTime.now().toString(),
                                    ),
                                  ),
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
                      const Spacer(),
                      Container(
                        width: 36.r,
                        height: 36.r,
                        decoration: const BoxDecoration(
                          color: AppStyle.bgGrey,
                          shape: BoxShape.circle,
                        ),
                        child: const Center(
                          child: Icon(Remix.bank_card_2_line),
                        ),
                      ),
                    ],
                  ),
                  Padding(
                    padding: EdgeInsets.only(left: 14.w),
                    child: Column(
                      children: [
                        Container(
                          width: 4.r,
                          height: 4.r,
                          margin: EdgeInsets.only(bottom: 6.h, top: 2.h),
                          decoration: const BoxDecoration(
                            color: AppStyle.tabBarBorderColor,
                            shape: BoxShape.circle,
                          ),
                        ),
                        Container(
                          width: 4.r,
                          height: 4.r,
                          margin: EdgeInsets.only(bottom: 6.h),
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
                            imageUrl: order.user?.img ?? "",
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
                            width: MediaQuery.sizeOf(context).width - 124.w,
                            child: Text(
                              order.address?.address ?? "",
                              style: AppStyle.interSemi(
                                size: 14.sp,
                                letterSpacing: -0.3,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.visible,
                            ),
                          ),
                          2.verticalSpace,
                          SizedBox(
                            width: MediaQuery.sizeOf(context).width - 124.w,
                            child: Row(
                              children: [
                                Expanded(
                                  child: AutoSizeText(
                                    order.user == null
                                        ? AppHelpers.getTranslation(
                                            TrKeys.deletedUser,
                                          )
                                        : order.user?.firstname ?? "",
                                    style: AppStyle.interNormal(
                                      size: 14.sp,
                                      letterSpacing: -0.3,
                                    ),
                                    maxLines: 1,
                                    minFontSize: 14,
                                  ),
                                ),
                                SizedBox(
                                  height: 12.r,
                                  child: const VerticalDivider(
                                    width: 8,
                                    thickness: 1,
                                  ),
                                ),
                                Expanded(
                                  child: AutoSizeText(
                                    order.user?.phone ?? "",
                                    style: AppStyle.interNormal(
                                      size: 14.sp,
                                      letterSpacing: -0.3,
                                    ),
                                    maxLines: 1,
                                    minFontSize: 14,
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
              ),
            ),
            16.verticalSpace,
            Divider(color: AppStyle.shimmerBase),
            8.verticalSpace,
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.w),
              child: Row(
                children: [
                  SvgPicture.asset("assets/svg/cutter.svg", width: 18.r),
                  10.horizontalSpace,
                  Expanded(
                    child: AutoSizeText(
                      AppHelpers.numberFormat(number: order.totalPrice ?? 0),
                      style: AppStyle.interSemi(size: 14.sp),
                      maxLines: 1,
                    ),
                  ),
                  Icon(Remix.takeaway_fill, size: 18.sp),
                  10.horizontalSpace,
                  Expanded(
                    child: AutoSizeText(
                      AppHelpers.numberFormat(number: order.deliveryFee ?? 0),
                      style: AppStyle.interSemi(size: 14.sp),
                      maxLines: 1,
                    ),
                  ),
                  Container(
                    width: 36.r,
                    height: 36.r,
                    decoration: const BoxDecoration(
                      color: AppStyle.bgGrey,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Remix.arrow_right_s_line),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
