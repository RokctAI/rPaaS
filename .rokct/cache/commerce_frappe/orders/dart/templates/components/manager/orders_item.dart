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
import 'package:remixicon/remixicon.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:base_sdk/src/services/enums.dart';
import 'package:${package}/presentation/components/orders/driver_avatar.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/services/app_helpers.dart';

class OrdersItem extends StatelessWidget {
  final String profileAvatar;
  final String name;
  final String number;
  final String time;
  final String price;
  final String paymentType;
  final OrderStatus status;
  final VoidCallback onTap;

  const OrdersItem({
    super.key,
    required this.profileAvatar,
    required this.name,
    required this.number,
    required this.time,
    required this.price,
    required this.status,
    required this.onTap,
    this.paymentType = '',
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 132.h,
        width: double.infinity,
        margin: EdgeInsets.only(bottom: 10.h),
        padding: EdgeInsets.all(16.r),
        decoration: BoxDecoration(
          color: AppStyle.white,
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                DriverAvatar(
                  imageUrl: profileAvatar,
                  name: name,
                  desc: AppHelpers.getTranslation(TrKeys.delivery),
                ),
                Row(
                  children: [
                    Text(
                      paymentType,
                      style: AppStyle.interSemi(
                        size: 12.sp,
                        letterSpacing: -0.3,
                      ),
                    ),
                    status == OrderStatus.delivered
                        ? const SizedBox.shrink()
                        : status == OrderStatus.canceled
                        ? Container(
                            width: 10.r,
                            height: 10.r,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.red,
                            ),
                          )
                        : Container(
                            padding: EdgeInsets.symmetric(
                              horizontal: 8.w,
                              vertical: 6.h,
                            ),
                            decoration: BoxDecoration(
                              color: AppStyle.bgGrey,
                              borderRadius: BorderRadius.circular(100.r),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                Icon(Remix.time_fill, size: 16.r),
                                4.horizontalSpace,
                                Text(
                                  "41:00",
                                  style: AppStyle.interSemi(
                                    size: 14.sp,
                                    color: AppStyle.blackColor,
                                  ),
                                ),
                              ],
                            ),
                          ),
                  ],
                ),
              ],
            ),
            const Divider(color: AppStyle.bgGrey),
            IntrinsicHeight(
              child: Row(
                children: [
                  Text(
                    number,
                    style: AppStyle.interNormal(
                      size: 14.sp,
                      color: AppStyle.blackColor,
                    ),
                  ),
                  const VerticalDivider(color: AppStyle.bgGrey),
                  Text(
                    time,
                    style: AppStyle.interNormal(
                      size: 14.sp,
                      color: AppStyle.blackColor,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    "\$$price",
                    style: AppStyle.interNormal(
                      size: 14.sp,
                      color: AppStyle.blackColor,
                    ),
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
