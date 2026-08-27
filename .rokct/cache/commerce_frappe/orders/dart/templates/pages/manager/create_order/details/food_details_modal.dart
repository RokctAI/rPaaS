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

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'widgets/food_extras.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'widgets/food_price_widget.dart';
import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'widgets/w_ingredient.dart';
import 'package:base_sdk/src/presentation/components/helper/common_image.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';
import 'package:orders_sdk/src/manager/application/order_products/order_products_provider.dart';
import 'package:orders_sdk/src/manager/application/product/products_provider.dart';

class FoodDetailsModal extends ConsumerStatefulWidget {
  final ProductData product;
  final ScrollController controller;

  const FoodDetailsModal({
    super.key,
    required this.product,
    required this.controller,
  });

  @override
  ConsumerState<FoodDetailsModal> createState() => _FoodDetailsModalState();
}

class _FoodDetailsModalState extends ConsumerState<FoodDetailsModal> {
  @override
  void initState() {
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref
          .read(productsProvider.notifier)
          .setProductDetails(
            product: widget.product,
            cartStocks: ref.watch(orderCartProvider).stocks,
          ),
    );
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: SingleChildScrollView(
        controller: widget.controller,
        physics: const BouncingScrollPhysics(),
        child: Consumer(
          builder: (context, ref, child) {
            final state = ref.watch(productsProvider);
            final event = ref.read(productsProvider.notifier);
            final cartEvent = ref.read(orderCartProvider.notifier);
            final productsEvent = ref.read(orderProductsProvider.notifier);
            return Column(
              children: [
                Padding(
                  padding: REdgeInsets.symmetric(horizontal: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const ModalDrag(),
                      CommonImage(
                        url: widget.product.img,
                        radius: 16,
                        errorRadius: 16,
                        fit: BoxFit.fitWidth,
                        height: 212,
                        width: double.infinity,
                      ),
                      22.verticalSpace,
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              widget.product.translation?.title ?? '',
                              style: AppStyle.interNormal(
                                size: 14.sp,
                                color: AppStyle.blackColor,
                                letterSpacing: -0.3,
                              ),
                            ),
                          ),
                          FoodPriceWidget(
                            product: widget.product,
                            stock: state.selectedStock,
                          ),
                        ],
                      ),
                      6.verticalSpace,
                      Text(
                        '${widget.product.translation?.description}',
                        style: AppStyle.interNormal(
                          size: 12.sp,
                          color: AppStyle.textGrey,
                          letterSpacing: -0.3,
                        ),
                      ),
                      24.verticalSpace,
                      if (ref.watch(productsProvider).typedExtras.isNotEmpty)
                        Padding(
                          padding: REdgeInsets.only(bottom: 24),
                          child: const FoodExtras(),
                        ),
                      WIngredientScreen(
                        list: state.selectedStock?.addons ?? [],
                        onChange: (int value) {
                          event.updateIngredient(context, value);
                        },
                        add: (int value) {
                          event.addIngredient(context, value);
                        },
                        remove: (int value) {
                          event.removeIngredient(context, value);
                        },
                      ),
                      16.verticalSpace,
                    ],
                  ),
                ),
                Container(
                  color: AppStyle.white,
                  padding: REdgeInsets.only(
                    bottom: Platform.isIOS ? 40 : 20,
                    top: 20,
                  ),
                  child: state.stockCount > 0
                      ? Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              width: 56.w,
                              height: 50.r,
                              decoration: BoxDecoration(
                                color: AppStyle.primary,
                                borderRadius: BorderRadius.only(
                                  topRight: Radius.circular(16.r),
                                  bottomRight: Radius.circular(16.r),
                                ),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                '${state.stockCount * (state.productData?.interval ?? 1)} ${state.productData?.unit?.translation?.title ?? ""}',
                                style: AppStyle.interSemi(
                                  size: 15.sp,
                                  color: AppStyle.blackColor,
                                ),
                              ),
                            ),
                            Row(
                              children: [
                                ButtonsBouncingEffect(
                                  child: GestureDetector(
                                    onTap: () => event.decreaseStockCount(
                                      updateCart: (count) =>
                                          cartEvent.addStockToCart(
                                            count: count,
                                            product: state.productData,
                                            stock: state.selectedStock,
                                            updateProducts: (stocks) =>
                                                productsEvent.updateProducts(
                                                  cartStocks: stocks,
                                                ),
                                          ),
                                    ),
                                    child: Container(
                                      height: 50.r,
                                      width: 100.r,
                                      decoration: BoxDecoration(
                                        color: const Color(
                                          0xFFF3F3F3,
                                        ) /* legacy Style.discountColor */,
                                        borderRadius: BorderRadius.only(
                                          topLeft: Radius.circular(16.r),
                                          bottomLeft: Radius.circular(16.r),
                                        ),
                                      ),
                                      alignment: Alignment.center,
                                      child: Icon(
                                        Remix.subtract_line,
                                        size: 24.r,
                                        color: AppStyle.blackColor,
                                      ),
                                    ),
                                  ),
                                ),
                                1.horizontalSpace,
                                ButtonsBouncingEffect(
                                  child: GestureDetector(
                                    onTap: () => event.increaseStockCount(
                                      updateCart: (count) =>
                                          cartEvent.addStockToCart(
                                            count: count,
                                            product: state.productData,
                                            stock: state.selectedStock,
                                            updateProducts: (stocks) =>
                                                productsEvent.updateProducts(
                                                  cartStocks: stocks,
                                                ),
                                          ),
                                    ),
                                    child: Container(
                                      height: 50.r,
                                      width: 100.r,
                                      decoration: BoxDecoration(
                                        color: const Color(
                                          0xFFF7F7F7,
                                        ) /* legacy Style.addCountColor */,
                                        borderRadius: BorderRadius.only(
                                          topRight: Radius.circular(16.r),
                                          bottomRight: Radius.circular(16.r),
                                        ),
                                      ),
                                      alignment: Alignment.center,
                                      child: Icon(
                                        Remix.add_line,
                                        size: 24.r,
                                        color: AppStyle.blackColor,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            36.horizontalSpace,
                          ],
                        )
                      : Padding(
                          padding: REdgeInsets.symmetric(horizontal: 16),
                          child: CustomButton(
                            title: AppHelpers.getTranslation(TrKeys.toBuy),
                            onPressed: () {
                              event.increaseStockCount(
                                updateCart: (count) {
                                  cartEvent.addStockToCart(
                                    count: count,
                                    product: state.productData,
                                    stock: state.selectedStock,
                                    updateProducts: (stocks) => productsEvent
                                        .updateProducts(cartStocks: stocks),
                                  );
                                },
                              );
                            },
                          ),
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
