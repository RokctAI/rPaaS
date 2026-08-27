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
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/presentation/components/extras/color_extras.dart';
import 'package:base_sdk/src/presentation/components/extras/image_extras.dart';
import 'package:base_sdk/src/presentation/components/extras/text_extras.dart';
import 'package:base_sdk/src/services/enums.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';
import 'package:orders_sdk/src/manager/application/product/products_provider.dart';

class FoodExtras extends ConsumerWidget {
  const FoodExtras({super.key}) ;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(productsProvider);
    final cartState = ref.watch(orderCartProvider);
    final event = ref.read(productsProvider.notifier);
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: state.typedExtras.isEmpty ? AppStyle.transparent : AppStyle.white,
        borderRadius: BorderRadius.circular(10.r),
      ),
      padding: REdgeInsets.symmetric(horizontal: 16, vertical: 26),
      child: ListView.builder(
        physics: const NeverScrollableScrollPhysics(),
        shrinkWrap: true,
        itemCount: state.typedExtras.length,
        padding: EdgeInsets.zero,
        itemBuilder: (context, index) {
          final TypedExtra typedExtra = state.typedExtras[index];
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (index != 0) 36.verticalSpace,
              Text(
                typedExtra.title,
                style: AppStyle.interSemi(
                  size: 16,
                  color: AppStyle.blackColor,
                  letterSpacing: -0.5,
                ),
              ),
              6.verticalSpace,
              typedExtra.type == ExtrasType.text
                  ? TextExtras(
                      uiExtras: typedExtra.uiExtras,
                      groupIndex: typedExtra.groupIndex,
                      onUpdate: (uiExtra) => event.updateSelectedIndexes(
                        typedExtra.groupIndex,
                        uiExtra.index,
                        cartStocks: cartState.stocks,
                      ),
                    )
                  : typedExtra.type == ExtrasType.color
                      ? ColorExtras(
                          uiExtras: typedExtra.uiExtras,
                          groupIndex: typedExtra.groupIndex,
                          onUpdate: (uiExtra) => event.updateSelectedIndexes(
                            typedExtra.groupIndex,
                            uiExtra.index,
                            cartStocks: cartState.stocks,
                          ),
                        )
                      : typedExtra.type == ExtrasType.image
                          ? ImageExtras(
                              uiExtras: typedExtra.uiExtras,
                              groupIndex: typedExtra.groupIndex,
                              // The manager create-order modal keeps no
                              // active-image state, so the required callback
                              // is a no-op (selection is handled by onUpdate).
                              updateImage: (_) {},
                              onUpdate: (uiExtra) =>
                                  event.updateSelectedIndexes(
                                typedExtra.groupIndex,
                                uiExtra.index,
                                cartStocks: cartState.stocks,
                              ),
                            )
                          : const SizedBox.shrink(),
            ],
          );
        },
      ),
    );
  }
}
