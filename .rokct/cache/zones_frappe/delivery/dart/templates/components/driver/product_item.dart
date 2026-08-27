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
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

class ProductItem extends StatelessWidget {
  final Product? product;
  final num? amount;
  final String price;

  const ProductItem(
      {super.key,
      required this.product,
      required this.amount,
      required this.price});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product?.translation?.title ?? "",
                    style: AppStyle.interSemi(size: 14.sp, color: AppStyle.black),
                  ),
                  4.verticalSpace,
                  Text(
                    "${AppHelpers.getTranslation(TrKeys.amount)} — ${(amount ?? 1) * (product?.interval ?? 1)} ${(product?.unit?.translation?.title ?? "")}",
                    style: AppStyle.interRegular(size: 14.sp, color: AppStyle.black),
                  ),
                ],
              ),
            ),
            Text(
              price,
              style: AppStyle.interSemi(size: 14.sp, color: AppStyle.black),
            ),
          ],
        ),
        product?.translation?.description != null
            ? Column(
                children: [
                  16.verticalSpace,
                  SizedBox(
                    width: 200.w,
                    child: RichText(
                      text: TextSpan(
                          text:
                              "${AppHelpers.getTranslation(TrKeys.sideDish)}:",
                          style:
                              AppStyle.interSemi(size: 14.sp, color: AppStyle.black),
                          children: [
                            TextSpan(
                              text: product?.translation?.description ?? "",
                              style: AppStyle.interRegular(
                                  size: 14.sp, color: AppStyle.black),
                            ),
                          ]),
                    ),
                  ),
                ],
              )
            : const SizedBox.shrink(),
      ],
    );
  }
}
