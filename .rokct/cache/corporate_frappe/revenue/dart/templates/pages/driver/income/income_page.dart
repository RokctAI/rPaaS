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

import 'package:auto_route/annotations.dart';
import 'package:charts_flutter/flutter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:revenue_sdk/src/driver/application/statistics/statistics_provider.dart';
import 'package:revenue_sdk/src/driver/application/statistics/statistics_state.dart';
import 'package:revenue_sdk/src/driver/infrastructure/models/chart.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/custom_tab_bar.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:${package}/presentation/pages/income/app_bar_screen.dart';
import 'package:${package}/presentation/pages/income/statistics_screen.dart';
import 'package:${package}/presentation/pages/income/widgets/income_item.dart';

@RoutePage(name: 'DriverIncomeRoute')
class IncomePage extends ConsumerStatefulWidget {
  const IncomePage({super.key});

  @override
  ConsumerState<IncomePage> createState() => _IncomePageState();
}

class _IncomePageState extends ConsumerState<IncomePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  final _tabs = [
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.today),
      ),
    ),
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.weekly),
      ),
    ),
    Tab(
      child: Text(
        AppHelpers.getTranslation(TrKeys.monthly),
      ),
    ),
  ];

  @override
  void initState() {
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 0) {
        ref.read(statisticsProvider.notifier).fetchStatistics(
            startTime: DateTime.now(), endTime: DateTime.now());
      } else if (_tabController.index == 1) {
        ref.read(statisticsProvider.notifier).fetchStatistics(
            startTime: DateTime.now(),
            endTime: DateTime.now().subtract(const Duration(days: 7)));
      } else {
        ref.read(statisticsProvider.notifier).fetchStatistics(
            startTime: DateTime.now(),
            endTime: DateTime.now().subtract(const Duration(days: 30)));
      }
    });
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        ref.read(statisticsProvider.notifier).fetchStatistics(
            startTime: DateTime.now(), endTime: DateTime.now());
      },
    );
    super.initState();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(statisticsProvider);
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          AbbBarScreen(event: ref.read(statisticsProvider.notifier)),
          16.verticalSpace,
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                  right: 16.w,
                  left: 16.w,
                  bottom: MediaQuery.paddingOf(context).bottom + 56.h),
              child: Column(
                children: [
                  CustomTabBar(
                    tabController: _tabController,
                    tabs: _tabs,
                  ),
                  24.verticalSpace,
                  _orderPrices(context, state),
                  TitleAndIcon(
                    title: AppHelpers.getTranslation(
                        TrKeys.deliverymanTransactions),
                  ),
                  12.verticalSpace,
                  IncomeItem(
                    title: AppHelpers.getTranslation(TrKeys.wallet),
                    price: AppHelpers.numberFormat(
                        number: LocalStorage.getUser()?.wallet?.price ?? 0),
                  ),
                  // The legacy host row showed the courier's rating from
                  // LocalStorage.getUser()?.rate (UserData parsed
                  // assign_reviews_avg_rating). base_sdk's ProfileData carries
                  // no rating field, so the row is parked until the courier
                  // profile slice (delivery_sdk, S-D3) owns that surface.
                  // IncomeItem(
                  //   title: AppHelpers.getTranslation(TrKeys.rating),
                  //   price: "-",
                  // ),
                  24.verticalSpace,
                  StatisticsScreen(
                      totalOrders: (state.countData?.data?.totalCount ?? 0)
                          .toString(),
                      todayOrders: (state.countData?.data?.totalTodayCount ?? 0)
                          .toString(),
                      acceptedOrders: (state
                                  .countData?.data?.totalAcceptedCount ??
                              0)
                          .toString(),
                      rejectedOrders: (state
                                  .countData?.data?.totalCanceledCount ??
                              0)
                          .toString(),
                      doneOrders: (state.countData?.data?.totalDeliveredCount ??
                              0)
                          .toString(),
                      canceledOrders:
                          (state
                                      .countData?.data?.totalNewCount ??
                                  0)
                              .toString(),
                      acceptedPer:
                          "${((state.countData?.data?.totalAcceptedCount ?? 0) / (state.countData?.data?.totalCount ?? 1) * 100).toStringAsFixed(1)}%",
                      rejectedPer:
                          "${((state.countData?.data?.totalCanceledCount ?? 0) / (state.countData?.data?.totalCount ?? 1) * 100).toStringAsFixed(1)}%",
                      donePer:
                          "${((state.countData?.data?.totalDeliveredCount ?? 0) / (state.countData?.data?.totalCount ?? 1) * 100).toStringAsFixed(1)}%",
                      canceledPer:
                          "${((state.countData?.data?.totalNewCount ?? 0) / (state.countData?.data?.totalCount ?? 1) * 100).toStringAsFixed(1)}%"),
                  32.verticalSpace,
                  _chart(state),
                ],
              ),
            ),
          ),
        ],
      ),
      floatingActionButtonLocation:
          FloatingActionButtonLocation.miniCenterDocked,
      floatingActionButton: Padding(
        padding: REdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            PopButton(),
            8.horizontalSpace,
            Expanded(
              child: CustomButton(
                title: AppHelpers.getTranslation(TrKeys.withdrawMoney),
                onPressed: () {},
              ),
            ),
          ],
        ),
      ),
    );
  }

  Column _chart(StatisticsState state) {
    // The SDK's StatisticsNotifier emits plain OrdinalSales rows so
    // revenue_sdk stays chart-library-agnostic; the charts_flutter Series
    // (including the brand-primary bar color the legacy host notifier set) is
    // built here, in the HOST package, whose pubspec owns charts_flutter.
    final List<Series<OrdinalSales, String>> series = [
      Series<OrdinalSales, String>(
        id: 'chart',
        data: state.chartData,
        domainFn: (OrdinalSales sales, _) => sales.day,
        measureFn: (OrdinalSales sales, _) => sales.sales,
        seriesColor: ColorUtil.fromDartColor(AppStyle.primary),
      ),
    ];
    return Column(
      children: [
        TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.earningsChart)),
        16.verticalSpace,
        Container(
            width: double.infinity,
            height: 300.h,
            decoration: BoxDecoration(
              color: AppStyle.white,
              borderRadius: BorderRadius.circular(10.r),
            ),
            padding: EdgeInsets.all(16.r),
            child: BarChart(
              series,
              animate: true,
              vertical: false,
              animationDuration: const Duration(seconds: 1),
              defaultRenderer: BarRendererConfig(
                  cornerStrategy: const ConstCornerStrategy(6)),
            )),
        32.verticalSpace,
      ],
    );
  }

  Column _orderPrices(BuildContext context, StatisticsState state) {
    return Column(
      children: [
        Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(10.r),
          ),
          padding: EdgeInsets.all(16.r),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                AppHelpers.getTranslation(TrKeys.orderPrice),
                style: AppStyle.interNormal(
                    size: 14,
                    color: AppStyle.blackColor,
                    letterSpacing: -0.3),
              ),
              16.verticalSpace,
              Text(
                AppHelpers.numberFormat(
                    number: state.countData?.data?.lastOrderTotalPrice ?? 0),
                style: AppStyle.interSemi(
                    size: 32,
                    color: AppStyle.blackColor,
                    letterSpacing: -0.3),
              ),
              4.verticalSpace,
              RichText(
                  text: TextSpan(
                      text: AppHelpers.getTranslation(TrKeys.lastIncome),
                      style: AppStyle.interNormal(
                          size: 12,
                          color: AppStyle.blackColor,
                          letterSpacing: -0.3),
                      children: [
                    TextSpan(
                      text: AppHelpers.numberFormat(
                          number: state.countData?.data?.lastOrderIncome ?? 0),
                      style: AppStyle.interSemi(
                          size: 12,
                          color: AppStyle.blackColor,
                          letterSpacing: -0.3),
                    )
                  ])),
            ],
          ),
        ),
        32.verticalSpace,
      ],
    );
  }
}
