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
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'no_orders.dart';
import 'package:${package}/presentation/pages/orders/details/order_details_modal.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';
import 'package:${package}/presentation/components/orders/order_item.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:orders_sdk/src/manager/application/orders/appbar/home_appbar_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/new/new_orders_provider.dart';

class NewOrdersBody extends StatelessWidget {
  final ScrollController? scrollController;

  const NewOrdersBody({super.key, this.scrollController}) ;

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, child) {
        final event = ref.read(newOrdersProvider.notifier);
        final state = ref.watch(newOrdersProvider);
        final appbarState = ref.watch(homeAppbarProvider);
        return SmartRefresher(
          physics: const BouncingScrollPhysics(),
          controller: state.refreshController!,
          enablePullDown: true,
          enablePullUp: true,
          onLoading: () => event.fetchNewOrders(
              context: context, activeTabIndex: appbarState.index),
          onRefresh: () => event.fetchNewOrders(
            context: context,
            isRefresh: true,
            activeTabIndex: appbarState.index,
          ),
          child: state.isLoading
              ? const LoadingList(
                  horizontalPadding: 16,
                  verticalPadding: 16,
                )
              : state.orders.isNotEmpty
                  ? ListView.builder(
                      padding: REdgeInsets.only(
                          right: 16, left: 16, top: 16, bottom: 100),
                      shrinkWrap: true,
                      itemCount: state.orders.length,
                      controller: scrollController,
                      physics: const BouncingScrollPhysics(),
                      itemBuilder: (context, index) => OrderItem(
                        order: state.orders[index],
                        onTap: () => AppHelpers.showCustomModalBottomSheet(
                          paddingTop: MediaQuery.paddingOf(context).top + 60,
                          context: context,
                          radius: 12,
                          modal: OrderDetailsModal(
                            order: state.orders[index],
                            newOrdersController: state.refreshController,
                          ),
                          isDarkMode: true,
                        ),
                      ),
                    )
                  : const NoOrders(),
        );
      },
    );
  }
}
