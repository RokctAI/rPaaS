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
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/component/loading/text_loading.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class OrderProductItem extends StatelessWidget {
  final CurrencyData? currencyData;
  final OrderDetail orderDetail;
  final bool isLast;
  final bool isLoading;
  final Function() onToggle;

  const OrderProductItem({
    super.key,
    required this.orderDetail,
    required this.isLoading,
    required this.onToggle,
    this.isLast = false,
    required this.currencyData,
  });

  @override
  Widget build(BuildContext context) {
    num totalPrice = 0;
    totalPrice += (orderDetail.totalPrice ?? 0);
    orderDetail.addons?.forEach((element) {
      totalPrice += (element.totalPrice ?? 0);
    });
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        16.verticalSpace,
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  isLoading
                      ? const TextLoading(width: 200)
                      : SizedBox(
                          width: MediaQuery.sizeOf(context).width - 180.w,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                orderDetail
                                        .stock?.product?.translation?.title ??
                                    AppHelpers.getTranslation(TrKeys.noName),
                                style: AppStyle.interSemi(
                                    size: 14.sp, color: AppStyle.black),
                              ),
                              for (int i = 0;
                                  i < (orderDetail.addons?.length ?? 0);
                                  i++)
                                Padding(
                                  padding: EdgeInsets.only(top: 2.h),
                                  child: Text(
                                    "${orderDetail.addons?[i].stock?.product?.translation?.title} x ${orderDetail.addons?[i].quantity ?? 0}  ${AppHelpers.numberFormat(number: orderDetail.addons?[i].stock?.totalPrice ?? 0, symbol: currencyData?.symbol)}",
                                    style: AppStyle.interSemi(
                                        size: 12.sp, color: AppStyle.black),
                                  ),
                                )
                            ],
                          ),
                        ),
                  4.verticalSpace,
                  isLoading
                      ? const TextLoading(width: 150)
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${AppHelpers.getTranslation(TrKeys.amount)} — ${(orderDetail.quantity ?? 1) * (orderDetail.stock?.product?.interval ?? 1)} ${orderDetail.stock?.product?.unit?.translation?.title ?? ""} x ${AppHelpers.numberFormat(number: orderDetail.stock?.totalPrice ?? 0, symbol: currencyData?.symbol)}',
                              style: AppStyle.interRegular(
                                size: 14.sp,
                                color: AppStyle.black,
                              ),
                            ),
                          ],
                        ),
                ],
              ),
            ),
            if (orderDetail.shopBonus ?? false)
              Text(
                AppHelpers.getTranslation(TrKeys.shopBonus),
                style: AppStyle.interSemi(size: 14.sp, color: AppStyle.blue),
              )
            else if (orderDetail.bonus ?? false)
              Text(
                AppHelpers.getTranslation(TrKeys.bonus),
                style: AppStyle.interSemi(size: 14.sp, color: AppStyle.blue),
              )
            else
              Text(
                AppHelpers.numberFormat(number: totalPrice,
                    symbol: currencyData?.symbol),
                style: AppStyle.interSemi(size: 14.sp, color: AppStyle.black),
              ),
          ],
        ),
        if (!isLast)
          Divider(thickness: 1.r, height: 1.r, color: AppStyle.bgGrey),
        if (orderDetail.note != '') 5.verticalSpace,
        if (orderDetail.note != '')
          Text(
            "${AppHelpers.getTranslation(TrKeys.note)}: ${orderDetail.note}",
            style: AppStyle.interRegular(
              size: 14.sp,
              color: AppStyle.black,
            ),
          )
      ],
    );
  }
}
