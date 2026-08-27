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
import 'package:auto_route/auto_route.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_slidable/flutter_slidable.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';
import 'package:${package}/presentation/components/orders/food_stock_item.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/payment/order_payment_provider.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';
import 'package:orders_sdk/src/manager/application/order_products/order_products_provider.dart';

/// The create-order cart: title row, calculated stock list, and (when
/// [embedded]) the "next" button.
///
/// Extracted from OrderPage's body so the same pane serves both flows on the
/// SAME providers (orderCartProvider / orderPaymentProvider — no forked cart
/// state): pushed as its own page on phones (OrderPage wraps it in a Scaffold
/// with app bar and pop/next FAB), and embedded beside the product grid on
/// expanded windows, POS main_page style, where it recalculates whenever the
/// cart's stocks change instead of on route push.
class OrderPane extends ConsumerStatefulWidget {
  final bool embedded;

  const OrderPane({super.key, this.embedded = false});

  @override
  ConsumerState<OrderPane> createState() => _OrderPaneState();
}

class _OrderPaneState extends ConsumerState<OrderPane> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        ref.read(orderPaymentProvider.notifier).getCalculate(
              stocks: ref.watch(orderCartProvider).stocks,
              type: 'pickup',
            );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.embedded) {
      // Pushed OrderPage recalculates once on route entry; the embedded pane
      // stays on screen while products are added, so it follows the cart.
      // The cart notifier builds a new stocks list on every mutation, which
      // makes the identity check a change check.
      ref.listen(orderCartProvider, (previous, next) {
        if (previous?.stocks != next.stocks) {
          ref.read(orderPaymentProvider.notifier).getCalculate(
                stocks: next.stocks,
                type: 'pickup',
              );
        }
      });
    }
    final state = ref.watch(orderCartProvider);
    final event = ref.read(orderCartProvider.notifier);
    final paymentState = ref.watch(orderPaymentProvider);
    final paymentNotifier = ref.read(orderPaymentProvider.notifier);
    final productsEvent = ref.read(orderProductsProvider.notifier);
    return Column(
      children: [
        Padding(
          padding: REdgeInsets.only(
            left: 16,
            right: 16,
            top: 24,
            bottom: 16,
          ),
          child: TitleAndIcon(
            title: AppHelpers.getTranslation(TrKeys.orders),
            rightTitleColor: AppStyle.red,
            rightTitle: state.stocks.isEmpty
                ? null
                : AppHelpers.getTranslation(TrKeys.clearAllOrders),
            onRightTap: () {
              event.clearAll();
              productsEvent.updateProducts(cartStocks: []);
              paymentNotifier.clearAll();
              if (!widget.embedded) {
                Navigator.pop(context);
              }
            },
          ),
        ),
        Expanded(
          child: SlidableAutoCloseBehavior(
            child: paymentState.isCalculateLoading
                ? const LoadingList(itemPadding: 2)
                : ListView.builder(
                    padding: REdgeInsets.only(
                      bottom: MediaQuery.paddingOf(context).bottom + 68,
                    ),
                    shrinkWrap: true,
                    itemCount: paymentState.orderCalculate?.stocks?.length ?? 0,
                    physics: const BouncingScrollPhysics(),
                    itemBuilder: (context, index) => FoodStockItem(
                      product: paymentState.orderCalculate?.stocks?[index],
                      onDelete: () => event.deleteStockFromCart(
                        stock: paymentState.orderCalculate?.stocks?[index] ??
                            Stock(),
                        updateProducts: (stocks) =>
                            productsEvent.updateProducts(cartStocks: stocks),
                      ),
                    ),
                  ),
          ),
        ),
        if (widget.embedded && state.stocks.isNotEmpty)
          Padding(
            padding: REdgeInsets.only(left: 16, right: 16, bottom: 16),
            child: CustomButton(
              title: AppHelpers.getTranslation(TrKeys.next),
              onPressed: () =>
                  context.pushRoute(const ManagerShippingAddressRoute()),
            ),
          ),
      ],
    );
  }
}
