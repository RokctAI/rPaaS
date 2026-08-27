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
import 'package:flutter/rendering.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/adaptive/adaptive_shell.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'widgets/new_orders_body.dart';
import 'widgets/ready_orders_body.dart';
import 'widgets/accepted_orders_body.dart';
import 'widgets/on_a_way_orders_body.dart';
import 'widgets/board/orders_board_view.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/custom_tab_bar.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:merchants_sdk/src/manager/application/main/main_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/accepted/accepted_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/appbar/home_appbar_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/new/new_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/on_a_way/on_a_way_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/ready/ready_orders_provider.dart';

class OrdersHomePage extends ConsumerStatefulWidget {
  const OrdersHomePage({super.key});

  @override
  ConsumerState<OrdersHomePage> createState() => _OrdersHomePageState();
}

class _OrdersHomePageState extends ConsumerState<OrdersHomePage>
    with SingleTickerProviderStateMixin {
  TabController? _tabController;
  ScrollController? _newController;
  ScrollController? _acceptedController;
  ScrollController? _readyController;
  ScrollController? _onAWayController;

  final _tabs = [
    Tab(child: Icon(Remix.fire_fill, size: 22.r)),
    Tab(child: Icon(Remix.check_double_fill, size: 22.r)),
    Tab(child: Icon(Remix.time_fill, size: 22.r)),
    Tab(child: Icon(Remix.takeaway_fill, size: 22.r)),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _tabController?.addListener(() {
      if (!(_tabController?.indexIsChanging ?? false)) {
        String title = AppHelpers.getTranslation(TrKeys.newOrders);
        int count = ref.watch(newOrdersProvider).totalCount;
        switch (_tabController?.index) {
          case 0:
            title = AppHelpers.getTranslation(TrKeys.newOrders);
            count = ref.watch(newOrdersProvider).totalCount;
            break;
          case 1:
            title = AppHelpers.getTranslation(TrKeys.acceptedOrders);
            count = ref.watch(acceptedOrdersProvider).totalCount;
            break;
          case 2:
            title = AppHelpers.getTranslation(TrKeys.readyOrders);
            count = ref.watch(readyOrdersProvider).totalCount;
            break;
          case 3:
            title = AppHelpers.getTranslation(TrKeys.onAWayOrders);
            count = ref.watch(onAWayOrdersProvider).totalCount;
            break;
          default:
            title = AppHelpers.getTranslation(TrKeys.newOrders);
            count = ref.watch(newOrdersProvider).totalCount;
            break;
        }
        ref
            .read(homeAppbarProvider.notifier)
            .setAppbarDetails(title, count, index: _tabController?.index);
      }
    });
    _newController = ScrollController();
    _acceptedController = ScrollController();
    _readyController = ScrollController();
    _onAWayController = ScrollController();
    _newController?.addListener(() => listen(_newController));
    _acceptedController?.addListener(() => listen(_acceptedController));
    _readyController?.addListener(() => listen(_readyController));
    _onAWayController?.addListener(() => listen(_onAWayController));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(newOrdersProvider.notifier)
          .fetchNewOrders(
            context: context,
            activeTabIndex: ref.watch(homeAppbarProvider).index,
            updateTotal: (count) => ref
                .read(homeAppbarProvider.notifier)
                .setAppbarDetails(
                  AppHelpers.getTranslation(TrKeys.newOrders),
                  count,
                  index: 0,
                ),
          );
      ref.read(acceptedOrdersProvider.notifier).fetchAcceptedOrders();
      ref.read(readyOrdersProvider.notifier).fetchReadyOrders();
      ref.read(onAWayOrdersProvider.notifier).fetchOnAWayOrders();
    });
  }

  @override
  void dispose() {
    super.dispose();
    _tabController?.dispose();
    _newController?.removeListener(() => listen(_newController));
    _acceptedController?.removeListener(() => listen(_acceptedController));
    _readyController?.removeListener(() => listen(_readyController));
    _onAWayController?.removeListener(() => listen(_onAWayController));
    _newController?.dispose();
    _acceptedController?.dispose();
    _readyController?.dispose();
    _onAWayController?.dispose();
  }

  void listen(ScrollController? controller) {
    final direction = controller?.position.userScrollDirection;
    if (direction == ScrollDirection.reverse) {
      ref.read(mainProvider.notifier).changeScrolling(true);
    } else if (direction == ScrollDirection.forward) {
      ref.read(mainProvider.notifier).changeScrolling(false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isLtr = LocalStorage.getLangLtr();
    return Directionality(
      textDirection: isLtr ? TextDirection.ltr : TextDirection.rtl,
      // Phone/medium windows keep the four-tab queue untouched; expanded
      // (desktop/tablet-landscape) windows swap the tabs for the POS-style
      // six-column kanban board. Both layouts share the queue providers, so
      // resizing the window never refetches or loses queue state.
      child: AdaptiveShell(compact: _buildTabs, expanded: _buildBoard),
    );
  }

  Widget _buildBoard(BuildContext context) {
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          _appBar(),
          const Expanded(child: OrdersBoardView()),
        ],
      ),
    );
  }

  Widget _buildTabs(BuildContext context) {
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          _appBar(),
          16.verticalSpace,
          Padding(
            padding: REdgeInsets.symmetric(horizontal: 16),
            child: CustomTabBar(tabController: _tabController!, tabs: _tabs),
          ),
          Expanded(
            child: TabBarView(
              physics: const BouncingScrollPhysics(),
              controller: _tabController,
              children: [
                NewOrdersBody(scrollController: _newController),
                AcceptedOrdersBody(scrollController: _acceptedController),
                ReadyOrdersBody(scrollController: _readyController),
                OnAWayOrdersBody(scrollController: _onAWayController),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _appBar() {
    return CustomAppBar(
      bottomPadding: 16.r,
      child: GestureDetector(
        onTap: () {},
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            Container(
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: AppStyle.bgGrey,
              ),
              padding: REdgeInsets.all(12),
              child: Icon(
                Remix.dashboard_3_line,
                size: 20.r,
                color: AppStyle.blackColor,
              ),
            ),
            10.horizontalSpace,
            Consumer(
              builder: (context, ref, child) {
                final state = ref.watch(homeAppbarProvider);
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      state.title.isEmpty
                          ? AppHelpers.getTranslation(TrKeys.newOrders)
                          : state.title,
                      style: AppStyle.interNormal(size: 12.sp),
                    ),
                    Row(
                      children: [
                        Text(
                          '${state.totalCount} ${AppHelpers.getTranslation(TrKeys.orders).toLowerCase()}',
                          style: AppStyle.interSemi(
                            size: 14.sp,
                            color: AppStyle.blackColor,
                          ),
                        ),
                        Icon(
                          Icons.keyboard_arrow_down,
                          color: AppStyle.blackColor,
                          size: 20.r,
                        ),
                      ],
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
