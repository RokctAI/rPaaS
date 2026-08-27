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
import 'package:remixicon/remixicon.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/orders/widgets/no_orders.dart';
import 'package:${package}/presentation/pages/orders/details/order_details_modal.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/filter_screen.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';
import 'package:${package}/presentation/components/orders/order_item.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/order_provider.dart';

@RoutePage(name: 'ManagerOrderHistoryRoute')
class OrderHistoryPage extends ConsumerStatefulWidget {
  const OrderHistoryPage({super.key});

  @override
  ConsumerState<OrderHistoryPage> createState() => _OrderHistoryPageState();
}

class _OrderHistoryPageState extends ConsumerState<OrderHistoryPage> {
  late RefreshController _refreshController;

  @override
  void initState() {
    super.initState();
    _refreshController = RefreshController();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(orderProvider.notifier).fetchHistoryOrders(),
    );
  }

  @override
  void dispose() {
    super.dispose();
    _refreshController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(orderProvider);
    final event = ref.read(orderProvider.notifier);
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
                  '${AppHelpers.getTranslation(TrKeys.thereAre)} ${state.totalCount} ${AppHelpers.getTranslation(TrKeys.orders)}',
                  style: AppStyle.interRegular(
                    size: 12.sp,
                    letterSpacing: -0.3,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: SmartRefresher(
              physics: const BouncingScrollPhysics(),
              controller: _refreshController,
              enablePullDown: true,
              enablePullUp: true,
              onLoading: () => event.fetchHistoryOrders(
                refreshController: _refreshController,
              ),
              onRefresh: () => event.fetchHistoryOrders(
                refreshController: _refreshController,
                isRefresh: true,
              ),
              child: state.isLoading
                  ? const LoadingList(
                      horizontalPadding: 16,
                      verticalPadding: 16,
                    )
                  : state.orders.isNotEmpty
                  ? ListView.builder(
                      padding: REdgeInsets.only(
                        right: 16,
                        left: 16,
                        top: 16,
                        bottom: 86,
                      ),
                      shrinkWrap: true,
                      itemCount: state.orders.length,
                      physics: const BouncingScrollPhysics(),
                      itemBuilder: (context, index) => OrderItem(
                        isHistoryOrder: true,
                        order: state.orders[index],
                        onTap: () => AppHelpers.showCustomModalBottomSheet(
                          paddingTop: MediaQuery.paddingOf(context).top + 60,
                          context: context,
                          radius: 12,
                          modal: OrderDetailsModal(
                            isHistoryOrder: true,
                            order: state.orders[index],
                          ),
                          isDarkMode: true,
                        ),
                      ),
                    )
                  : const NoOrders(),
            ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: EdgeInsets.symmetric(horizontal: 16.w),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const PopButton(heroTag: AppConstants.heroTagOrderHistory),
            GestureDetector(
              onTap: () => AppHelpers.showCustomModalBottomSheet(
                paddingTop: MediaQuery.paddingOf(context).top,
                context: context,
                radius: 12,
                modal: FilterScreen(
                  onChangeDay: (rangeDatePicker) {
                    ref
                        .read(orderProvider.notifier)
                        .fetchHistoryOrders(
                          isRefresh: true,
                          start: rangeDatePicker.last,
                          end: rangeDatePicker.first,
                        );
                  },
                ),
                isDarkMode: true,
              ),
              child: Container(
                // Not const: AppStyle.primary is a getter (brand-injectable),
                // unlike the legacy Style.primary constant.
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppStyle.primary,
                ),
                padding: REdgeInsets.all(16),
                child: const Icon(Remix.equalizer_fill),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
