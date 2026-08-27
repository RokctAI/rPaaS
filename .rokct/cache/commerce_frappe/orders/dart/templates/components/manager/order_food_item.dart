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

import 'package:remixicon/remixicon.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/presentation/components/helper/common_image.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class OrderFoodItem extends StatelessWidget {
  final ProductData product;
  final Function() onTap;
  final int spacing;

  const OrderFoodItem({
    super.key,
    required this.product,
    required this.onTap,
    this.spacing = 1,
  });

  @override
  Widget build(BuildContext context) {
    final bool isOutOfStock = product.stocks == null || product.stocks!.isEmpty;
    final bool hasDiscount = isOutOfStock
        ? false
        : (product.stocks!.first.discount != null &&
              (product.stocks!.first.discount ?? 0) > 0);
    return ButtonsBouncingEffect(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          color: AppStyle.white,
          margin: EdgeInsets.only(bottom: spacing.r),
          padding: REdgeInsets.symmetric(vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                children: [
                  if ((product.cartCount ?? 0) > 0)
                    Container(
                      width: 50.r,
                      height: 78.r,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.only(
                          topRight: Radius.circular(16.r),
                          bottomRight: Radius.circular(16.r),
                        ),
                        color: AppStyle.primary,
                      ),
                      child: Text(
                        '${(product.cartCount ?? 1) * (product.interval ?? 1)} ${product.unit?.translation?.title ?? ""}',
                        style: AppStyle.interSemi(size: 15.sp),
                      ),
                    ),
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
                        isOutOfStock
                            ? Text(
                                AppHelpers.getTranslation(TrKeys.outOfStock),
                                style: AppStyle.interSemi(
                                  size: 11.sp,
                                  color: AppStyle.red,
                                  letterSpacing: -0.3,
                                ),
                              )
                            : (hasDiscount
                                  ? Row(
                                      children: [
                                        Text(
                                          AppHelpers.numberFormat(
                                            number:
                                                (product.stocks?.first.price ??
                                                    0) +
                                                (product.stocks?.first.tax ??
                                                    0),
                                          ),
                                          style: AppStyle.interSemi(
                                            size: 14.sp,
                                            color: AppStyle.blackColor,
                                            letterSpacing: -0.3,
                                            decoration:
                                                TextDecoration.lineThrough,
                                          ),
                                        ),
                                        10.horizontalSpace,
                                        Container(
                                          padding: REdgeInsets.only(
                                            top: 4,
                                            bottom: 4,
                                            left: 4,
                                            right: 10,
                                          ),
                                          decoration: BoxDecoration(
                                            borderRadius: BorderRadius.circular(
                                              30.r,
                                            ),
                                            color: AppStyle.redBg,
                                          ),
                                          alignment: Alignment.center,
                                          child: Row(
                                            children: [
                                              Container(
                                                width: 20.r,
                                                height: 20.r,
                                                decoration: const BoxDecoration(
                                                  shape: BoxShape.circle,
                                                  color: AppStyle.red,
                                                ),
                                                child: Icon(
                                                  Remix.percent_fill,
                                                  size: 12.r,
                                                  color: AppStyle.white,
                                                ),
                                              ),
                                              8.horizontalSpace,
                                              Text(
                                                AppHelpers.numberFormat(
                                                  number:
                                                      product
                                                          .stocks
                                                          ?.first
                                                          .totalPrice ??
                                                      0,
                                                ),
                                                style: AppStyle.interSemi(
                                                  size: 14.sp,
                                                  color: AppStyle.blackColor,
                                                  letterSpacing: -0.3,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    )
                                  : Text(
                                      AppHelpers.numberFormat(
                                        number:
                                            product.stocks?.first.totalPrice ??
                                            0,
                                      ),
                                      style: AppStyle.interSemi(
                                        size: 14.sp,
                                        color: AppStyle.blackColor,
                                        letterSpacing: -0.3,
                                      ),
                                    )),
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
              8.verticalSpace,
            ],
          ),
        ),
      ),
    );
  }
}
