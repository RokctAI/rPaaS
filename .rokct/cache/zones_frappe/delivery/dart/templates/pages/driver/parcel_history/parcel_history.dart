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
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:delivery_sdk/src/driver/application/parcel/parcel_provider.dart';
import 'package:${package}/presentation/pages/parcel/parcel_item.dart';

import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/component/filter_screen.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

@RoutePage()
class ParcelHistoryPage extends ConsumerStatefulWidget {
  const ParcelHistoryPage({super.key});

  @override
  ConsumerState<ParcelHistoryPage> createState() => _ParcelHistoryPageState();
}

class _ParcelHistoryPageState extends ConsumerState<ParcelHistoryPage> {
  late RefreshController historyController;

  @override
  void initState() {
    historyController = RefreshController();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(parcelProvider.notifier).fetchHistoryOrders(context);
    });
    super.initState();
  }

  @override
  void dispose() {
    historyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(parcelProvider);
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          CustomAppBar(
            bottomPadding: 16.h,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  AppHelpers.getTranslation(TrKeys.orderHistory),
                  style: AppStyle.interSemi(size: 18.sp),
                ),
                Text(
                  AppHelpers.getTranslation(TrKeys.thereAreOrders),
                  style: AppStyle.interRegular(
                    size: 12.sp,
                    letterSpacing: -0.3,
                  ),
                ),
              ],
            ),
          ),
          state.isHistoryLoading
              ? const Padding(
                  padding: EdgeInsets.only(top: 32),
                  child: Loading(),
                )
              : Expanded(
                  child: SmartRefresher(
                    enablePullDown: true,
                    enablePullUp: true,
                    onRefresh: () {
                      ref
                          .read(parcelProvider.notifier)
                          .fetchHistoryOrdersPage(
                            context,
                            historyController,
                            isRefresh: true,
                          );
                    },
                    onLoading: () {
                      ref
                          .read(parcelProvider.notifier)
                          .fetchHistoryOrdersPage(context, historyController);
                    },
                    controller: historyController,
                    child: ListView.builder(
                      padding: EdgeInsets.only(
                        left: 16.r,
                        right: 16.r,
                        top: 30.h,
                        bottom: MediaQuery.paddingOf(context).bottom + 42.h,
                      ),
                      shrinkWrap: true,
                      itemCount: state.historyOrders.length,
                      physics: const BouncingScrollPhysics(),
                      itemBuilder: (context, index) {
                        return ParcelItem(
                          isOrder: false,
                          parcel: state.historyOrders[index],
                          isSet: false,
                        );
                      },
                    ),
                  ),
                ),
        ],
      ),
      floatingActionButtonLocation:
          FloatingActionButtonLocation.miniCenterFloat,
      floatingActionButton: Padding(
        padding: EdgeInsets.symmetric(horizontal: 16.w),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const PopButton(),
            GestureDetector(
              onTap: () {
                AppHelpers.showCustomModalBottomSheet(
                  paddingTop: MediaQuery.paddingOf(context).top,
                  context: context,
                  radius: 12,
                  modal: const FilterScreen(parcel: true),
                  isDarkMode: true,
                );
              },
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppStyle.primary,
                ),
                padding: EdgeInsets.all(16.r),
                child: const Icon(Remix.equalizer_fill),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
