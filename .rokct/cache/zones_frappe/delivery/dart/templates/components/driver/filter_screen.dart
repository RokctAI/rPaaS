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

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:delivery_sdk/src/driver/application/parcel/parcel_provider.dart';
import 'package:revenue_sdk/src/driver/application/statistics/statistics_provider.dart';

import 'package:delivery_sdk/src/driver/application/order/order_provider.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'custom_date_picker.dart';
import 'package:base_sdk/src/presentation/components/custom_tab_bar.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';

class FilterScreen extends StatefulWidget {
  final bool isTabBar;
  final bool parcel;
  final DateTime? start;
  final DateTime? end;

  const FilterScreen(
      {super.key,
      this.isTabBar = true,
      this.start,
      this.end,
      this.parcel = false});

  @override
  State<FilterScreen> createState() => _FilterScreenState();
}

class _FilterScreenState extends State<FilterScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<DateTime?> _rangeDatePicker = [];
  List<DateTime?> _newList = [];

  final _tabs = [
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.today),
      ),
    ),
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.weekly),
        maxLines: 1,
        overflow: TextOverflow.clip,
      ),
    ),
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.monthly),
        maxLines: 1,
        overflow: TextOverflow.clip,
      ),
    ),
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.overall),
      ),
    ),
  ];

  @override
  void initState() {
    _tabController = TabController(length: 4, vsync: this);
    _rangeDatePicker = [
      widget.start ?? DateTime.now(),
      widget.end ?? DateTime.now(),
    ];
    _tabController.addListener(() {
      switch (_tabController.index) {
        case 0:
          _rangeDatePicker = [
            DateTime.now(),
            DateTime.now(),
          ];
          _newList = _rangeDatePicker;
          break;
        case 1:
          _rangeDatePicker = [
            DateTime.now().subtract(const Duration(days: 7)),
            DateTime.now(),
          ];
          _newList = _rangeDatePicker;
          break;
        case 2:
          _rangeDatePicker = [
            DateTime.now().subtract(const Duration(days: 30)),
            DateTime.now(),
          ];
          _newList = _rangeDatePicker;
          break;
        case 3:
          _rangeDatePicker = [
            DateTime.now().subtract(const Duration(days: 120)),
            DateTime.now(),
          ];
          _newList = _rangeDatePicker;
          break;
      }
      setState(() {});
    });
    super.initState();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: EdgeInsets.symmetric(horizontal: 16.w),
          child: TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.filter)),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: 16.w),
          child: Text(
            AppHelpers.getTranslation(TrKeys.selectDesiredOrderHistory),
            style: AppStyle.interNormal(
                size: 14.sp, color: AppStyle.black, letterSpacing: -0.3),
          ),
        ),
        widget.isTabBar
            ? Padding(
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 24.h),
                child: CustomTabBar(
                  isScrollable: true,
                  tabController: _tabController,
                  tabs: _tabs,
                ),
              )
            : const SizedBox.shrink(),
        CustomDatePicker(
          range: _rangeDatePicker,
          onChange: (n) {
            _newList = n;
          },
        ),
        16.verticalSpace,
        Padding(
          padding: EdgeInsets.symmetric(horizontal: 16.w),
          child: Consumer(builder: (context, ref, child) {
            return CustomButton(
                title: AppHelpers.getTranslation(TrKeys.save),
                onPressed: () {
                  widget.isTabBar
                      ? widget.parcel
                          ? ref
                              .read(parcelProvider.notifier)
                              .fetchHistoryOrders(context,
                                  start: _newList.first, end: _newList.last)
                          : ref.read(orderProvider.notifier).fetchHistoryOrders(
                              context,
                              start: _newList.first,
                              end: _newList.last)
                      : ref.read(statisticsProvider.notifier).fetchStatistics(
                          startTime: _newList.last ?? DateTime.now(),
                          endTime: _newList.first ?? DateTime.now());
                  context.router.maybePop();
                });
          }),
        ),
        8.verticalSpace,
      ],
    );
  }
}
