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
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'board_order_column.dart';
import 'package:${package}/presentation/pages/orders/details/order_details_modal.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/enums.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/orders/accepted/accepted_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/board/orders_board_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/canceled/canceled_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/delivered/delivered_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/new/new_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/on_a_way/on_a_way_orders_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/ready/ready_orders_provider.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';

/// The wide-screen order queue: POS's kanban board (`board_view.dart` in
/// admin_desktop), minus its cooking column — the manager state machine is
/// new -> accepted -> ready -> on_a_way -> delivered, plus canceled.
///
/// A horizontally scrollable row of six fixed-width status columns. Cards are
/// long-press-dragged forward along the state machine (Flutter's own
/// Draggable/DragTarget — no drag_and_drop_lists dependency); the drop calls
/// the same `updateOrderStatus` repository call the order-details modal's
/// swipe button uses, then refreshes the source and target columns.
///
/// The four active queues reuse the exact providers behind the phone tabs, so
/// tab and board stay in sync when the window is resized. Delivered and
/// canceled are board-only columns with their own providers, fetched here.
class OrdersBoardView extends ConsumerStatefulWidget {
  const OrdersBoardView({super.key});

  @override
  ConsumerState<OrdersBoardView> createState() => _OrdersBoardViewState();
}

class _OrdersBoardViewState extends ConsumerState<OrdersBoardView> {
  final ScrollController _boardController = ScrollController();

  /// The seller state machine, in column order. Drops are legal only from an
  /// earlier column to a later one (POS's `newListIndex > oldListIndex` rule),
  /// which also permits canceling from any active column.
  static const List<OrderStatus> _flow = [
    OrderStatus.open,
    OrderStatus.accepted,
    OrderStatus.ready,
    OrderStatus.onWay,
    OrderStatus.delivered,
    OrderStatus.canceled,
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        // The four active queues are fetched by OrdersHomePage; only the
        // board-only history columns are fetched here.
        ref
            .read(deliveredOrdersProvider.notifier)
            .fetchDeliveredOrders(isRefresh: true);
        ref
            .read(canceledOrdersProvider.notifier)
            .fetchCanceledOrders(isRefresh: true);
      },
    );
  }

  @override
  void dispose() {
    _boardController.dispose();
    super.dispose();
  }

  void _refreshColumn(OrderStatus status) {
    switch (status) {
      case OrderStatus.open:
        // activeTabIndex -1: no tab is active on the board, so the notifier
        // must not poke the tab layout's pull-to-refresh controller.
        ref.read(newOrdersProvider.notifier).fetchNewOrders(
              context: context,
              isRefresh: true,
              activeTabIndex: -1,
            );
        break;
      case OrderStatus.accepted:
        ref
            .read(acceptedOrdersProvider.notifier)
            .fetchAcceptedOrders(isRefresh: true);
        break;
      case OrderStatus.ready:
        ref.read(readyOrdersProvider.notifier).fetchReadyOrders(isRefresh: true);
        break;
      case OrderStatus.onWay:
        ref
            .read(onAWayOrdersProvider.notifier)
            .fetchOnAWayOrders(isRefresh: true);
        break;
      case OrderStatus.delivered:
        ref
            .read(deliveredOrdersProvider.notifier)
            .fetchDeliveredOrders(isRefresh: true);
        break;
      case OrderStatus.canceled:
        ref
            .read(canceledOrdersProvider.notifier)
            .fetchCanceledOrders(isRefresh: true);
        break;
    }
  }

  Future<void> _loadMoreColumn(OrderStatus status) {
    switch (status) {
      case OrderStatus.open:
        return ref.read(newOrdersProvider.notifier).fetchNewOrders(
              context: context,
              activeTabIndex: -1,
            );
      case OrderStatus.accepted:
        return ref.read(acceptedOrdersProvider.notifier).fetchAcceptedOrders();
      case OrderStatus.ready:
        return ref.read(readyOrdersProvider.notifier).fetchReadyOrders();
      case OrderStatus.onWay:
        return ref.read(onAWayOrdersProvider.notifier).fetchOnAWayOrders();
      case OrderStatus.delivered:
        return ref
            .read(deliveredOrdersProvider.notifier)
            .fetchDeliveredOrders();
      case OrderStatus.canceled:
        return ref.read(canceledOrdersProvider.notifier).fetchCanceledOrders();
    }
  }

  bool _canAccept(OrderStatus target, BoardDragData data) {
    if (data.order.id == null) {
      return false;
    }
    return _flow.indexOf(target) > _flow.indexOf(data.from);
  }

  void _onAccept(OrderStatus target, BoardDragData data) {
    final String? orderId = data.order.id;
    if (orderId == null) {
      return;
    }
    ref.read(ordersBoardProvider.notifier).updateOrderStatus(
          context,
          orderId: orderId,
          status: target,
          success: () {
            _refreshColumn(data.from);
            _refreshColumn(target);
          },
        );
  }

  void _openDetails(OrderStatus status, OrderData order) {
    final bool isHistory =
        status == OrderStatus.delivered || status == OrderStatus.canceled;
    AppHelpers.showCustomModalBottomSheet(
      paddingTop: MediaQuery.paddingOf(context).top + 60,
      context: context,
      radius: 12,
      modal: OrderDetailsModal(
        order: order,
        isHistoryOrder: isHistory ? true : null,
      ),
      isDarkMode: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    final updatingIds = ref.watch(ordersBoardProvider).updatingIds;
    final newState = ref.watch(newOrdersProvider);
    final acceptedState = ref.watch(acceptedOrdersProvider);
    final readyState = ref.watch(readyOrdersProvider);
    final onAWayState = ref.watch(onAWayOrdersProvider);
    final deliveredState = ref.watch(deliveredOrdersProvider);
    final canceledState = ref.watch(canceledOrdersProvider);

    Widget column({
      required OrderStatus status,
      required String title,
      required Color color,
      required bool isLoading,
      required List<OrderData> orders,
      required int count,
    }) {
      return BoardOrderColumn(
        title: title,
        count: count,
        color: color,
        isLoading: isLoading,
        orders: orders,
        status: status,
        updatingIds: updatingIds,
        onRefresh: () => _refreshColumn(status),
        onLoadMore: () => _loadMoreColumn(status),
        onOrderTap: (order) => _openDetails(status, order),
        canAccept: (data) => _canAccept(status, data),
        onAccept: (data) => _onAccept(status, data),
      );
    }

    return Scrollbar(
      controller: _boardController,
      thumbVisibility: true,
      scrollbarOrientation: ScrollbarOrientation.bottom,
      child: SingleChildScrollView(
        controller: _boardController,
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            column(
              status: OrderStatus.open,
              title: AppHelpers.getTranslation(TrKeys.newOrders),
              color: AppStyle.blue,
              isLoading: newState.isLoading,
              orders: newState.orders,
              count: newState.totalCount,
            ),
            column(
              status: OrderStatus.accepted,
              title: AppHelpers.getTranslation(TrKeys.acceptedOrders),
              color: AppStyle.blueBonus,
              isLoading: acceptedState.isLoading,
              orders: acceptedState.orders,
              count: acceptedState.totalCount,
            ),
            column(
              status: OrderStatus.ready,
              title: AppHelpers.getTranslation(TrKeys.readyOrders),
              color: AppStyle.rate,
              isLoading: readyState.isLoading,
              orders: readyState.orders,
              count: readyState.totalCount,
            ),
            column(
              status: OrderStatus.onWay,
              title: AppHelpers.getTranslation(TrKeys.onAWayOrders),
              color: AppStyle.black,
              isLoading: onAWayState.isLoading,
              orders: onAWayState.orders,
              count: onAWayState.totalCount,
            ),
            column(
              status: OrderStatus.delivered,
              title: AppHelpers.getTranslation(TrKeys.delivered),
              color: AppStyle.green,
              isLoading: deliveredState.isLoading,
              orders: deliveredState.orders,
              count: deliveredState.totalCount,
            ),
            column(
              status: OrderStatus.canceled,
              title: AppHelpers.getTranslation(TrKeys.canceled),
              color: AppStyle.red,
              isLoading: canceledState.isLoading,
              orders: canceledState.orders,
              count: canceledState.totalCount,
            ),
          ],
        ),
      ),
    );
  }
}
