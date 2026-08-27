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
import 'package:revenue_sdk/src/driver/application/statistics/statistics_notifier.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/filter_screen.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

class AbbBarScreen extends StatelessWidget {
  // base_sdk's FilterScreen requires an onChangeDay callback (the host copy's
  // calendar sheet fired nothing), so the page passes its notifier in — same
  // wiring as the manager income template's AppbarScreen.
  final StatisticsNotifier event;

  const AbbBarScreen({super.key, required this.event});

  @override
  Widget build(BuildContext context) {
    return CustomAppBar(
        bottomPadding: 16.h,
        child: GestureDetector(
          onTap: () {},
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text(
                    AppHelpers.getTranslation(TrKeys.income),
                    style: AppStyle.interSemi(size: 18),
                  ),
                  Text(
                    AppHelpers.getTranslation(TrKeys.earningsRestaurant),
                    style: AppStyle.interRegular(size: 12, letterSpacing: -0.3),
                  ),
                ],
              ),
              GestureDetector(
                onTap: () {
                  AppHelpers.showCustomModalBottomSheet(
                      paddingTop: MediaQuery.paddingOf(context).top,
                      context: context,
                      radius: 12,
                      modal: FilterScreen(
                        isTabBar: false,
                        onChangeDay: (rangeDatePicker) {
                          event.fetchStatistics(
                            startTime: rangeDatePicker.last ?? DateTime.now(),
                            endTime: rangeDatePicker.first ?? DateTime.now(),
                          );
                        },
                      ),
                      isDarkMode: true);
                },
                child: Container(
                  padding: EdgeInsets.all(10.r),
                  decoration: const BoxDecoration(
                      color: AppStyle.bgGrey, shape: BoxShape.circle),
                  child: const Icon(
                    Remix.calendar_event_fill,
                    color: AppStyle.blackColor,
                  ),
                ),
              )
            ],
          ),
        ));
  }
}
