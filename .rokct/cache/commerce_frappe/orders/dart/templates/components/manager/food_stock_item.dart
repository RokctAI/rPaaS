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
import 'package:flutter_slidable/flutter_slidable.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/presentation/components/helper/common_image.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class FoodStockItem extends StatelessWidget {
  final Stock? product;
  final Function() onDelete;

  const FoodStockItem({
    super.key,
    required this.product,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppStyle.white,
      margin: REdgeInsets.only(bottom: 1),
      padding: REdgeInsets.symmetric(vertical: 12),
      child: Slidable(
        endActionPane: ActionPane(
          extentRatio: 0.12,
          motion: const ScrollMotion(),
          children: [
            Expanded(
              child: Builder(
                builder: (context) {
                  return GestureDetector(
                    onTap: () {
                      Slidable.of(context)?.close();
                      onDelete();
                    },
                    child: Container(
                      width: 50.r,
                      height: 78.r,
                      decoration: BoxDecoration(
                        color: AppStyle.red,
                        borderRadius: BorderRadius.only(
                          topLeft: Radius.circular(16.r),
                          bottomLeft: Radius.circular(16.r),
                        ),
                      ),
                      alignment: Alignment.center,
                      child: Icon(
                        Remix.close_fill,
                        color: AppStyle.white,
                        size: 24.r,
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
        child: Row(
          children: [
            if ((product?.quantity ?? 0) > 0)
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
                  '${(product?.quantity ?? 1) * (product?.stock?.product?.interval ?? 1)} ${product?.stock?.product?.unit?.translation?.title ?? ""}',
                  style: AppStyle.interSemi(size: 15.sp),
                ),
              ),
            16.horizontalSpace,
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product?.stock?.product?.translation?.title ?? '',
                    style: AppStyle.interNormal(
                      size: 14.sp,
                      color: AppStyle.black,
                      letterSpacing: -0.3,
                    ),
                  ),
                  8.verticalSpace,
                  Text(
                    product?.stock?.product?.translation?.description ?? '',
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                    style: AppStyle.interNormal(
                      size: 12.sp,
                      color: AppStyle.textGrey,
                      letterSpacing: -0.3,
                    ),
                  ),
                  ...?product?.stock?.extras?.map(
                    (e) => Padding(
                      padding: REdgeInsets.only(right: 4, top: 4),
                      child: Row(
                        children: [
                          Text(
                            "${e.group?.translation?.title ?? ''}: ",
                            style: AppStyle.interNormal(
                              size: 12.sp,
                              color: AppStyle.textGrey,
                              letterSpacing: -0.3,
                            ),
                          ),
                          Text(
                            AppHelpers.getTranslation(e.value ?? ''),
                            style: AppStyle.interNormal(
                              size: 12.sp,
                              color: AppStyle.black,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  ...?product?.addons?.map(
                    (e) => Padding(
                      padding: REdgeInsets.only(right: 4, top: 4),
                      child: Row(
                        children: [
                          Text(
                            e.product?.translation?.title ?? '',
                            style: AppStyle.interNormal(
                              size: 12.sp,
                              color: AppStyle.textGrey,
                              letterSpacing: -0.3,
                            ),
                          ),
                          Text(
                            "  ${AppHelpers.numberFormat(number: (e.totalPrice ?? 0) / (e.quantity ?? 1))} x ${e.quantity ?? 1}",
                            style: AppStyle.interNormal(
                              size: 12.sp,
                              color: AppStyle.black,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  8.verticalSpace,
                  if (product?.shopBonus ?? false)
                    Text(
                      AppHelpers.getTranslation(TrKeys.shopBonus),
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        color: AppStyle.black,
                        letterSpacing: -0.3,
                      ),
                    )
                  else if (product?.bonus ?? false)
                    Text(
                      AppHelpers.getTranslation(TrKeys.bonus),
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        color: AppStyle.black,
                        letterSpacing: -0.3,
                      ),
                    )
                  else
                    Text(
                      AppHelpers.numberFormat(number: product?.totalPrice),
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        color: AppStyle.black,
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
              url: product?.stock?.product?.img,
              radius: 0,
              errorRadius: 0,
              fit: BoxFit.fitWidth,
            ),
            16.horizontalSpace,
          ],
        ),
      ),
    );
  }
}
