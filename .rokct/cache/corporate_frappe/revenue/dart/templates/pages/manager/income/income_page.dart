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

// import 'package:charts_flutter_new/flutter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:${package}/presentation/theme/theme.dart';
import 'package:${package}/presentation/pages/income/widgets/chart.dart';
import 'package:${package}/presentation/pages/income/widgets/statistics_section.dart';
import 'package:${package}/presentation/pages/income/widgets/order_prices_section.dart';
import 'package:${package}/presentation/pages/income/app_bar_screen.dart';
import 'package:revenue_sdk/src/manager/application/statistics/statistics_provider.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/custom_tab_bar.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';

@RoutePage(name: 'ManagerIncomeRoute')
class ManagerIncomePage extends ConsumerStatefulWidget {
  const ManagerIncomePage({super.key});

  @override
  ConsumerState<ManagerIncomePage> createState() => _IncomePageState();
}

class _IncomePageState extends ConsumerState<ManagerIncomePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  final _tabs = [
    Tab(child: Text(AppHelpers.getTranslation(TrKeys.today))),
    Tab(child: Text(AppHelpers.getTranslation(TrKeys.weekly))),
    Tab(child: Text(AppHelpers.getTranslation(TrKeys.monthly))),
  ];

  @override
  void initState() {
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 0) {
        ref
            .read(statisticsProvider.notifier)
            .fetchStatistics(
              startTime: DateTime.now(),
              endTime: DateTime.now(),
            );
      } else if (_tabController.index == 1) {
        ref
            .read(statisticsProvider.notifier)
            .fetchStatistics(
              startTime: DateTime.now(),
              endTime: DateTime.now().subtract(const Duration(days: 7)),
            );
      } else {
        ref
            .read(statisticsProvider.notifier)
            .fetchStatistics(
              startTime: DateTime.now(),
              endTime: DateTime.now().subtract(const Duration(days: 30)),
            );
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(statisticsProvider.notifier)
          .fetchStatistics(startTime: DateTime.now(), endTime: DateTime.now());
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
    return Scaffold(
      backgroundColor: AppStyle.textGrey,
      body: Column(
        children: [
          AppbarScreen(event: ref.read(statisticsProvider.notifier)),
          16.verticalSpace,
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: EdgeInsets.only(
                right: 16.w,
                left: 16.w,
                bottom: MediaQuery.of(context).padding.bottom + 56.h,
              ),
              child: Column(
                children: [
                  CustomTabBar(tabController: _tabController, tabs: _tabs),
                  24.verticalSpace,
                  OrderPricesSection(
                    startTime: DateTime.now(),
                    endTime: DateTime.now().subtract(
                      Duration(
                        days: _tabController.index == 0
                            ? 0
                            : _tabController.index == 1
                            ? 7
                            : 30,
                      ),
                    ),
                  ),
                  if (ref
                          .watch(statisticsProvider)
                          .countData
                          ?.chart
                          ?.isNotEmpty ??
                      false)
                    _chart(),
                  const StatisticsSection(),
                  20.verticalSpace,
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
        child: const Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          // base_sdk's PopButton dropped its Hero wrapper (and with it the
          // heroTag parameter, whose AppConstants.heroTagIncomePage tag is
          // also gone); the plain back button is the whole behavior now.
          children: [PopButton()],
        ),
      ),
    );
  }

  Column _chart() {
    return Column(
      children: [
        TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.earningsChart)),
        16.verticalSpace,
        Container(
          padding: REdgeInsets.symmetric(horizontal: 16, vertical: 18),
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(12.r),
          ),
          child: SalesChart(
            price: ref.watch(statisticsProvider).prices,
            chart: ref.watch(statisticsProvider).countData?.chart ?? [],
            times: ref.watch(statisticsProvider).time,
            isDay: _tabController.index == 0,
            isLoading: false,
          ),
        ),
        // 16.verticalSpace,
        // Container(
        //   width: double.infinity,
        //   height: 300.h,
        //   decoration: BoxDecoration(
        //     color: Style.white,
        //     borderRadius: BorderRadius.circular(10.r),
        //   ),
        //   padding: EdgeInsets.all(16.r),
        //   child: Consumer(builder: (context, ref, child) {
        //     final state = ref.watch(statisticsProvider);
        //     return BarChart(
        //       state.list,
        //       animate: true,
        //       vertical: false,
        //       animationDuration: const Duration(seconds: 1),
        //       defaultRenderer: BarRendererConfig(
        //           cornerStrategy: const ConstCornerStrategy(6)),
        //       selectionModels: [
        //         SelectionModelConfig(changedListener: (d) {
        //           // AppHelpers.showAlertDialog(
        //           //   context: context,
        //           //   child: Column(
        //           //     mainAxisSize: MainAxisSize.min,
        //           //     children: [
        //           //       Text((d.selectedSeries.first.data.first as OrdinalSales)
        //           //           .day),
        //           //       8.verticalSpace,
        //           //       Text(
        //           //           "${AppHelpers.trans(TrKeys.price)}: ${(d.selectedSeries.first.data.first as OrdinalSales).sales}"),
        //           //     ],
        //           //   ),
        //           // );
        //         })
        //       ],
        //     );
        //   }),
        // ),
        32.verticalSpace,
      ],
    );
  }
}

