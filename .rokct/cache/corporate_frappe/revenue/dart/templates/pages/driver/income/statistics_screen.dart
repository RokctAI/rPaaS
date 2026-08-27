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
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:${package}/presentation/pages/income/widgets/statistics_item.dart';

class StatisticsScreen extends StatelessWidget {
  final String totalOrders;
  final String todayOrders;
  final String acceptedOrders;
  final String rejectedOrders;
  final String doneOrders;
  final String canceledOrders;
  final String acceptedPer;
  final String rejectedPer;
  final String donePer;
  final String canceledPer;

  const StatisticsScreen({
    super.key,
    required this.totalOrders,
    required this.todayOrders,
    required this.acceptedOrders,
    required this.rejectedOrders,
    required this.doneOrders,
    required this.canceledOrders,
    required this.acceptedPer,
    required this.rejectedPer,
    required this.donePer,
    required this.canceledPer,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.statistics)),
        16.verticalSpace,
        SizedBox(
          height: 190.h,
          child: Row(
            children: [
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10.r),
                  color: AppStyle.white,
                ),
                padding: EdgeInsets.all(12.r),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppHelpers.getTranslation(TrKeys.totalOrders),
                      style: AppStyle.interNormal(
                          size: 12,
                          color: AppStyle.blackColor,
                          letterSpacing: -0.3),
                    ),
                    const Spacer(),
                    Text(
                      totalOrders,
                      style: AppStyle.interSemi(
                          size: 34,
                          color: AppStyle.blackColor,
                          letterSpacing: -1),
                    ),
                    RichText(
                      text: TextSpan(
                          text: AppHelpers.getTranslation(TrKeys.today),
                          style: AppStyle.interNormal(
                              size: 12,
                              color: AppStyle.blackColor,
                              letterSpacing: -0.3),
                          children: [
                            TextSpan(
                              text: " $todayOrders",
                              style: AppStyle.interSemi(
                                  size: 12,
                                  color: AppStyle.blackColor,
                                  letterSpacing: -0.3),
                            )
                          ]),
                    )
                  ],
                ),
              ),
              8.horizontalSpace,
              Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      StatisticsItem(
                          title:
                              AppHelpers.getTranslation(TrKeys.acceptedOrders),
                          count: acceptedOrders,
                          percentage:
                              acceptedPer == "NaN%" ? "0%" : acceptedPer,
                          bgColor: AppStyle.green,
                          textColor: AppStyle.white,
                          iconColor: AppStyle.white.withOpacity(0.54)),
                      8.horizontalSpace,
                      StatisticsItem(
                          title:
                              AppHelpers.getTranslation(TrKeys.rejectedOrders),
                          count: rejectedOrders,
                          percentage:
                              rejectedPer == "NaN%" ? "0%" : rejectedPer,
                          bgColor: AppStyle.red,
                          textColor: AppStyle.white,
                          iconColor: AppStyle.white.withOpacity(0.54)),
                    ],
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      StatisticsItem(
                          title: AppHelpers.getTranslation(TrKeys.doneOrders),
                          count: doneOrders,
                          percentage: donePer == "NaN%" ? "0%" : donePer,
                          bgColor: AppStyle.white,
                          textColor: AppStyle.blackColor,
                          iconColor: AppStyle.icons),
                      8.horizontalSpace,
                      StatisticsItem(
                        title: AppHelpers.getTranslation(TrKeys.newOrders),
                        count: canceledOrders,
                        percentage: canceledPer == "NaN%" ? "0%" : canceledPer,
                        bgColor: AppStyle.white,
                        textColor: AppStyle.blackColor,
                        iconColor: AppStyle.icons,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        )
      ],
    );
  }
}
