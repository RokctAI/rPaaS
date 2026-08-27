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

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';
import 'package:${package}/presentation/components/orders/order_item.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/enums.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';

/// Payload carried while an order card is dragged between board columns:
/// the order plus the column it left, so the drop target can decide whether
/// the move is a legal forward transition.
class BoardDragData {
  final OrderData order;
  final OrderStatus from;

  const BoardDragData({required this.order, required this.from});
}

/// One status column of the wide-screen order board.
///
/// Fixed-width analog of the POS `board_view.dart` DragAndDropList, built on
/// Flutter's own [LongPressDraggable]/[DragTarget] so the composed host needs
/// no extra package. Widths and board chrome use plain logical pixels (not
/// ScreenUtil units) for the same reason base_sdk's `windowSizeOf` does: on a
/// desktop window the phone design-size scale would balloon them.
class BoardOrderColumn extends StatefulWidget {
  /// Column width in logical pixels (POS used 235; a little wider fits the
  /// manager's order card).
  static const double width = 260;

  final String title;
  final int count;
  final Color color;
  final bool isLoading;
  final List<OrderData> orders;
  final OrderStatus status;

  /// Ids of orders whose status change is in flight — their cards are dimmed
  /// and locked.
  final Set<String> updatingIds;

  final VoidCallback onRefresh;
  final Future<void> Function() onLoadMore;
  final void Function(OrderData order) onOrderTap;
  final bool Function(BoardDragData data) canAccept;
  final void Function(BoardDragData data) onAccept;

  const BoardOrderColumn({
    super.key,
    required this.title,
    required this.count,
    required this.color,
    required this.isLoading,
    required this.orders,
    required this.status,
    required this.updatingIds,
    required this.onRefresh,
    required this.onLoadMore,
    required this.onOrderTap,
    required this.canAccept,
    required this.onAccept,
  });

  @override
  State<BoardOrderColumn> createState() => _BoardOrderColumnState();
}

class _BoardOrderColumnState extends State<BoardOrderColumn> {
  bool _loadingMore = false;

  bool _onScroll(ScrollNotification notification) {
    if (!_loadingMore &&
        notification.metrics.extentAfter < 300 &&
        widget.orders.isNotEmpty) {
      _loadingMore = true;
      widget.onLoadMore().whenComplete(() {
        _loadingMore = false;
      });
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: BoardOrderColumn.width,
      margin: const EdgeInsets.only(right: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _header(),
          const SizedBox(height: 8),
          Expanded(
            child: DragTarget<BoardDragData>(
              onWillAcceptWithDetails: (details) =>
                  widget.canAccept(details.data),
              onAcceptWithDetails: (details) => widget.onAccept(details.data),
              builder: (context, candidates, rejected) => Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: candidates.isNotEmpty
                        ? widget.color
                        : AppStyle.transparent,
                    width: 2,
                  ),
                ),
                child: widget.isLoading
                    // LoadingList is shrink-wrapped and non-scrollable, so it
                    // needs a scroll parent to not overflow a short column.
                    ? const SingleChildScrollView(
                        physics: NeverScrollableScrollPhysics(),
                        child: LoadingList(
                          itemCount: 4,
                          horizontalPadding: 4,
                          verticalPadding: 4,
                        ),
                      )
                    : widget.orders.isEmpty
                        ? _empty()
                        : _list(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppStyle.white,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: widget.color,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              widget.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppStyle.interSemi(
                size: 14,
                color: AppStyle.blackColor,
              ),
            ),
          ),
          Text(
            widget.count.toString(),
            style: AppStyle.interSemi(
              size: 14,
              color: AppStyle.textGrey,
            ),
          ),
          const SizedBox(width: 4),
          InkWell(
            borderRadius: BorderRadius.circular(15),
            onTap: widget.onRefresh,
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Icon(
                Remix.refresh_line,
                size: 18,
                color: AppStyle.blackColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _empty() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Text(
          AppHelpers.getTranslation(TrKeys.noOrders),
          textAlign: TextAlign.center,
          style: AppStyle.interNormal(
            size: 13,
            color: AppStyle.textGrey,
          ),
        ),
      ),
    );
  }

  Widget _list() {
    return NotificationListener<ScrollNotification>(
      onNotification: _onScroll,
      child: ListView.builder(
        padding: const EdgeInsets.only(top: 2, bottom: 24, left: 2, right: 2),
        physics: const BouncingScrollPhysics(),
        itemCount: widget.orders.length,
        itemBuilder: (context, index) => _card(widget.orders[index]),
      ),
    );
  }

  Widget _card(OrderData order) {
    final card = OrderItem(
      order: order,
      isHistoryOrder: widget.status == OrderStatus.delivered ||
          widget.status == OrderStatus.canceled,
      onTap: () => widget.onOrderTap(order),
    );
    final bool isUpdating = widget.updatingIds.contains(order.id);
    if (isUpdating) {
      return IgnorePointer(
        child: Opacity(opacity: 0.5, child: card),
      );
    }
    return LongPressDraggable<BoardDragData>(
      data: BoardDragData(order: order, from: widget.status),
      maxSimultaneousDrags: 1,
      feedback: Material(
        color: AppStyle.transparent,
        child: SizedBox(
          // Feedback floats in the overlay, outside this column's box
          // constraints, so it needs the width the card would have had.
          width: BoardOrderColumn.width - 4,
          child: Opacity(opacity: 0.9, child: card),
        ),
      ),
      childWhenDragging: Opacity(opacity: 0.35, child: card),
      child: card,
    );
  }
}
