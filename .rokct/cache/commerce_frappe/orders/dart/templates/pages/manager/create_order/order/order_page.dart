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
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/routes/app_router.dart';
import 'package:${package}/presentation/pages/create_order/order/widgets/order_pane.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/helper/shop_bordered_avatar.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';

@RoutePage(name: 'ManagerOrderRoute')
class OrderPage extends ConsumerStatefulWidget {
  const OrderPage({super.key});

  @override
  ConsumerState<OrderPage> createState() => _OrderPageState();
}

/// Phone flow: the cart pushed as its own route. The body (title, calculated
/// stock list, recalculation on entry) lives in [OrderPane], which the
/// create-order page embeds directly on expanded windows instead of pushing
/// this route.
class _OrderPageState extends ConsumerState<OrderPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          CustomAppBar(
            bottomPadding: 16.h,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                ShopBorderedAvatar(
                  size: 40,
                  imageSize: 33,
                  borderRadius: 20,
                  // base_sdk's LocalStorage keeps the shop as raw JSON (getShopJson) -
                  // same access pattern as merchants_sdk's main_page.
                  imageUrl: LocalStorage.getShopJson()?['logo_img'] as String?,
                ),
                12.horizontalSpace,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Text(
                        (LocalStorage.getShopJson()?['translation']?['title']
                                as String?) ??
                            '',
                        style: AppStyle.interSemi(size: 18.sp),
                      ),
                      Text(
                        (LocalStorage.getShopJson()?['translation']
                                ?['description'] as String?) ??
                            '',
                        style: AppStyle.interRegular(
                          size: 12.sp,
                          letterSpacing: -0.3,
                        ),
                        maxLines: 1,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Expanded(child: OrderPane()),
        ],
      ),
      floatingActionButtonLocation:
          FloatingActionButtonLocation.miniCenterDocked,
      floatingActionButton: Padding(
        padding: REdgeInsets.all(16),
        child: Consumer(
          builder: (context, ref, child) {
            final cartState = ref.watch(orderCartProvider);
            return Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const PopButton(heroTag: AppConstants.heroTagAddOrderButton),
                8.horizontalSpace,
                if (cartState.stocks.isNotEmpty)
                  Expanded(
                    child: CustomButton(
                      title: AppHelpers.getTranslation(TrKeys.next),
                      onPressed: () =>
                          context.pushRoute(const ManagerShippingAddressRoute()),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
