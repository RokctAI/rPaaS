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
import 'package:remixicon/remixicon.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:${package}/presentation/routes/app_router.dart';

import 'package:base_sdk/src/presentation/adaptive/adaptive_shell.dart';
import 'package:base_sdk/src/presentation/adaptive/split_pane.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/create_order/details/food_details_modal.dart';
import 'package:${package}/presentation/pages/create_order/order/widgets/order_pane.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/loading/tab_bar_loading.dart';
import 'package:base_sdk/src/presentation/components/categories_tab_bar.dart';
import 'package:${package}/presentation/components/orders/products_body.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/text_fields/search_text_field.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';
import 'package:orders_sdk/src/manager/application/order_products/categories/product_categories_provider.dart';
import 'package:orders_sdk/src/manager/application/order_products/order_products_provider.dart';

@RoutePage(name: 'ManagerCreateOrderRoute')
class CreateOrderPage extends ConsumerStatefulWidget {
  const CreateOrderPage({super.key});

  @override
  ConsumerState<CreateOrderPage> createState() => _CreateOrderPageState();
}

class _CreateOrderPageState extends ConsumerState<CreateOrderPage> {
  late RefreshController _categoryController;
  late RefreshController _productController;

  @override
  void initState() {
    super.initState();
    _categoryController = RefreshController();
    _productController = RefreshController();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(orderProductsProvider.notifier)
          .fetchProducts(
            categoryId: null,
            isRefresh: ref.watch(productCategoriesProvider).activeIndex != 1
                ? true
                : false,
            isOpeningPage: true,
            cartStocks: ref.watch(orderCartProvider).stocks,
          );
      ref.read(productCategoriesProvider.notifier).initialFetchCategories();
    });
  }

  @override
  void dispose() {
    super.dispose();
    _categoryController.dispose();
    _productController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool isLtr = LocalStorage.getLangLtr();
    return Directionality(
      textDirection: isLtr ? TextDirection.ltr : TextDirection.rtl,
      child: KeyboardDismisser(
        // Phone/medium windows keep the push-to-cart flow; expanded windows
        // show the POS main_page split: product grid beside the always-visible
        // cart pane. Both run on the same cart/payment providers, so a window
        // resize mid-order loses nothing.
        child: AdaptiveShell(compact: _buildCompact, expanded: _buildExpanded),
      ),
    );
  }

  Widget _buildCompact(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: AppStyle.bgGrey,
      body: _productsColumn(),
      floatingActionButtonLocation:
          FloatingActionButtonLocation.miniCenterDocked,
      floatingActionButton: Padding(
        padding: REdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: <Widget>[
            const PopButton(heroTag: AppConstants.heroTagAddOrderButton),
            Consumer(
              builder: (context, ref, child) {
                final cartState = ref.watch(orderCartProvider);
                return cartState.stocks.isNotEmpty
                    ? ButtonsBouncingEffect(
                        child: GestureDetector(
                          onTap: () =>
                              context.pushRoute(const ManagerOrderRoute()),
                          child: Container(
                            height: 48.r,
                            decoration: BoxDecoration(
                              color: AppStyle.primary,
                              borderRadius: BorderRadius.circular(10.r),
                            ),
                            padding: REdgeInsets.symmetric(horizontal: 16),
                            alignment: Alignment.center,
                            child: Row(
                              children: [
                                Text(
                                  AppHelpers.getTranslation(TrKeys.ordering),
                                  style: AppStyle.interSemi(
                                    size: 16.sp,
                                    color: AppStyle.blackColor,
                                  ),
                                ),
                                10.horizontalSpace,
                                Container(
                                  height: 32.r,
                                  padding: REdgeInsets.symmetric(
                                    horizontal: 14,
                                  ),
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                    color: AppStyle.blackColor,
                                    borderRadius: BorderRadius.circular(18.r),
                                  ),
                                  child: Text(
                                    AppHelpers.numberFormat(
                                      number: cartState.totalPrice,
                                    ),
                                    style: AppStyle.interSemi(
                                      size: 16.sp,
                                      color: AppStyle.white,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                    : const SizedBox.shrink();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExpanded(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: AppStyle.bgGrey,
      body: SplitPane(
        primary: _productsColumn(),
        secondary: Container(
          decoration: const BoxDecoration(
            border: Border(left: BorderSide(color: AppStyle.differBorderColor)),
          ),
          child: const OrderPane(embedded: true),
        ),
      ),
      floatingActionButtonLocation:
          FloatingActionButtonLocation.miniCenterDocked,
      // The cart lives beside the grid here, so no "ordering" push button —
      // only the pop button back out of the POS screen.
      floatingActionButton: Padding(
        padding: REdgeInsets.all(16),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: <Widget>[
            PopButton(heroTag: AppConstants.heroTagAddOrderButton),
          ],
        ),
      ),
    );
  }

  Widget _productsColumn() {
    return Column(
      children: [
        CustomAppBar(
          bottomPadding: 4.h,
          child: Consumer(
            builder: (context, ref, child) {
              final productsEvent = ref.read(orderProductsProvider.notifier);
              final categoriesState = ref.watch(productCategoriesProvider);
              return SearchTextField(
                onChanged: (value) => productsEvent.setQuery(
                  query: value,
                  categoryId: categoriesState.activeIndex == 1
                      ? null
                      : categoriesState
                            .categories[categoriesState.activeIndex - 2]
                            .id,
                  cartStocks: ref.watch(orderCartProvider).stocks,
                ),
                suffixIcon: Icon(
                  Remix.equalizer_fill,
                  color: AppStyle.blackColor,
                  size: 20.r,
                ),
              );
            },
          ),
        ),
        Expanded(
          child: Column(
            children: [
              24.verticalSpace,
              Consumer(
                builder: (context, ref, child) {
                  final categoriesState = ref.watch(productCategoriesProvider);
                  final categoriesEvent = ref.read(
                    productCategoriesProvider.notifier,
                  );
                  final productsEvent = ref.read(
                    orderProductsProvider.notifier,
                  );
                  return categoriesState.isLoading
                      ? const TabBarLoading()
                      : SizedBox(
                          height: 36.h,
                          child: CategoriesTabBar(
                            categories: categoriesState.categories,
                            activeIndex: categoriesState.activeIndex,
                            refreshController: _categoryController,
                            onChangeTab: (index) {
                              categoriesEvent.setActiveIndex(index);
                              if (index != categoriesState.activeIndex) {
                                productsEvent.fetchProducts(
                                  refreshController: _productController,
                                  categoryId: index == 1
                                      ? null
                                      : categoriesState
                                            .categories[index - 2]
                                            .id,
                                  isRefresh: true,
                                  cartStocks: ref
                                      .watch(orderCartProvider)
                                      .stocks,
                                );
                              }
                            },
                            onLoading: () =>
                                categoriesEvent.fetchMoreCategories(
                                  refreshController: _categoryController,
                                ),
                          ),
                        );
                },
              ),
              8.verticalSpace,
              Expanded(
                child: Consumer(
                  builder: (context, ref, child) {
                    final productsState = ref.watch(orderProductsProvider);
                    final categoriesState = ref.watch(
                      productCategoriesProvider,
                    );
                    final productsEvent = ref.read(
                      orderProductsProvider.notifier,
                    );
                    return ProductsBody(
                      loadingHeight: 130,
                      isOrderFoods: true,
                      isLoading: productsState.isLoading,
                      products: productsState.products,
                      refreshController: _productController,
                      onRefreshing: () => productsEvent.fetchProducts(
                        cartStocks: ref.watch(orderCartProvider).stocks,
                        refreshController: _productController,
                        isRefresh: true,
                        categoryId: categoriesState.activeIndex == 1
                            ? null
                            : categoriesState
                                  .categories[categoriesState.activeIndex - 2]
                                  .id,
                      ),
                      onLoading: () => productsEvent.fetchProducts(
                        refreshController: _productController,
                        cartStocks: ref.watch(orderCartProvider).stocks,
                        categoryId: categoriesState.activeIndex == 1
                            ? null
                            : categoriesState
                                  .categories[categoriesState.activeIndex - 2]
                                  .id,
                      ),
                      onProductTap: (index) =>
                          AppHelpers.showCustomModalBottomDragSheet(
                            paddingTop: 60,
                            context: context,
                            // base_sdk's drag sheet has no initSize knob -
                            // it opens at maxChildSize; legacy opened at 0.6.
                            maxChildSize: 0.8,
                            modal: (c) => FoodDetailsModal(
                              controller: c,
                              product: productsState.products[index],
                            ),
                          ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
