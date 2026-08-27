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

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/presentation/components/helper/common_image.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class FoodItem extends StatelessWidget {
  final ProductData product;
  final Function() onTap;
  final int spacing;

  const FoodItem({
    super.key,
    required this.product,
    required this.onTap,
    this.spacing = 1,
  });

  @override
  Widget build(BuildContext context) {
    final bool isOutOfStock = product.stocks == null || product.stocks!.isEmpty;
    return InkWell(
      onTap: onTap,
      child: Container(
        color: product.status == 'pending' ? AppStyle.pending : AppStyle.white,
        margin: EdgeInsets.only(bottom: spacing.r),
        padding: REdgeInsets.symmetric(vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(
              children: [
                16.horizontalSpace,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${product.translation?.title}',
                        style: AppStyle.interNormal(
                          size: 14.sp,
                          color: AppStyle.blackColor,
                          letterSpacing: -0.3,
                        ),
                      ),
                      8.verticalSpace,
                      Text(
                        '${product.translation?.description}',
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                        style: AppStyle.interNormal(
                          size: 12.sp,
                          color: AppStyle.textGrey,
                          letterSpacing: -0.3,
                        ),
                      ),
                      8.verticalSpace,
                      Text(
                        isOutOfStock
                            ? AppHelpers.getTranslation(TrKeys.outOfStock)
                            : AppHelpers.numberFormat(
                                number: product.stocks?.first.price ?? 0,
                              ),
                        style: AppStyle.interSemi(
                          size: 14.sp,
                          color: isOutOfStock
                              ? AppStyle.red
                              : AppStyle.blackColor,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
                ),
                8.horizontalSpace,
                CommonImage(
                  width: 110,
                  height: 106,
                  url: product.img,
                  radius: 0,
                  errorRadius: 0,
                  fit: BoxFit.fitWidth,
                ),
                16.horizontalSpace,
              ],
            ),
            20.verticalSpace,
            Padding(
              padding: REdgeInsets.symmetric(horizontal: 16),
              child: Divider(
                thickness: 1.r,
                height: 1.r,
                color: AppStyle.tabBarBorderColor,
              ),
            ),
            14.verticalSpace,
            Padding(
              padding: REdgeInsets.symmetric(horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  ButtonsBouncingEffect(
                    child: Row(
                      children: [
                        Text(
                          AppHelpers.getTranslation(TrKeys.parameters),
                          style: AppStyle.interNormal(size: 13.sp),
                        ),
                        6.horizontalSpace,
                        Icon(
                          Remix.arrow_down_s_line,
                          size: 18.r,
                          color: AppStyle.blackColor,
                        ),
                      ],
                    ),
                  ),
                  Container(
                    height: 30.r,
                    alignment: Alignment.center,
                    padding: REdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(10.r),
                      color: product.status == 'pending'
                          ? AppStyle.pendingDark
                          : AppStyle.primary,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          product.status == 'pending'
                              ? Remix.time_fill
                              : Remix.check_double_line,
                          size: 20.r,
                          color: AppStyle.white,
                        ),
                        6.horizontalSpace,
                        Text(
                          product.status == 'pending'
                              ? AppHelpers.getTranslation(TrKeys.pending)
                              : AppHelpers.getTranslation(TrKeys.published),
                          style: AppStyle.interNormal(
                            size: 14.sp,
                            color: AppStyle.white,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            8.verticalSpace,
          ],
        ),
      ),
    );
  }
}
