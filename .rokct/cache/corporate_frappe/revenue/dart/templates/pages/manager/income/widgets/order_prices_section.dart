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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

// @income-more-orders-import
import 'package:${package}/presentation/theme/theme.dart';
import 'package:revenue_sdk/src/manager/application/statistics/statistics_provider.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

class OrderPricesSection extends StatelessWidget {
  final DateTime? endTime;
  final DateTime? startTime;

  const OrderPricesSection({super.key, this.endTime, this.startTime});

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, child) {
        final state = ref.watch(statisticsProvider);
        return Column(
          children: [
            Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppStyle.white,
                borderRadius: BorderRadius.circular(10.r),
              ),
              padding: REdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    AppHelpers.getTranslation(TrKeys.orderPrice),
                    style: AppStyle.interNormal(
                      size: 14,
                      color: AppStyle.blackColor,
                      letterSpacing: -0.3,
                    ),
                  ),
                  16.verticalSpace,
                  Text(
                    AppHelpers.numberFormat(
                      number: state.countData?.lastOrderTotalPrice ?? 0,
                    ),
                    style: AppStyle.interSemi(
                      size: 32,
                      color: AppStyle.blackColor,
                      letterSpacing: -0.3,
                    ),
                  ),
                  4.verticalSpace,
                  RichText(
                    text: TextSpan(
                      text: AppHelpers.getTranslation(TrKeys.lastIncome),
                      style: AppStyle.interNormal(
                        size: 12,
                        color: AppStyle.blackColor,
                        letterSpacing: -0.3,
                      ),
                      children: [
                        TextSpan(
                          text: AppHelpers.numberFormat(
                            number: state.countData?.lastOrderIncome ?? 0,
                          ),
                          style: AppStyle.interSemi(
                            size: 12,
                            color: AppStyle.blackColor,
                            letterSpacing: -0.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            10.verticalSpace,
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  width: (MediaQuery.sizeOf(context).width - 40) / 2,
                  decoration: BoxDecoration(
                    color: AppStyle.blackColor,
                    borderRadius: BorderRadius.circular(10.r),
                  ),
                  padding: REdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        AppHelpers.getTranslation(TrKeys.restaurantRevenue),
                        style: AppStyle.interNormal(
                          size: 12,
                          color: AppStyle.white,
                          letterSpacing: -0.3,
                        ),
                      ),
                      Text(
                        AppHelpers.numberFormat(
                          number: state.countData?.totalPrice ?? 0,
                        ),
                        style: AppStyle.interSemi(
                          size: 20,
                          color: AppStyle.white,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: (MediaQuery.sizeOf(context).width - 40) / 2,
                  decoration: BoxDecoration(
                    color: AppStyle.blackColor,
                    borderRadius: BorderRadius.circular(10.r),
                  ),
                  padding: REdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        AppHelpers.getTranslation(TrKeys.fMRevenue),
                        style: AppStyle.interNormal(
                          size: 12,
                          color: AppStyle.white,
                          letterSpacing: -0.3,
                        ),
                      ),
                      Text(
                        AppHelpers.numberFormat(
                          number: state.countData?.fmTotalPrice ?? 0,
                        ),
                        style: AppStyle.interSemi(
                          size: 20,
                          color: AppStyle.white,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            10.verticalSpace,
            GestureDetector(
              onTap: () {
                // @income-more-orders-modal
              },
              child: Container(
                decoration: BoxDecoration(
                  color: AppStyle.white,
                  borderRadius: BorderRadius.circular(10.r),
                  boxShadow: [
                    BoxShadow(
                      spreadRadius: 0,
                      blurRadius: 2,
                      color: AppStyle.blackColor.withOpacity(0.04),
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                padding: EdgeInsets.all(16.r),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      AppHelpers.getTranslation(TrKeys.moreAboutOrders),
                      style: AppStyle.interNormal(
                        size: 14,
                        color: AppStyle.blackColor,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const Icon(Remix.arrow_right_s_line),
                  ],
                ),
              ),
            ),
            32.verticalSpace,
          ],
        );
      },
    );
  }
}

