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

import 'create_food_addons_modal.dart';
import 'create_food_edit_extras_modal.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/manager/application/foods/create/details/create_food_details_provider.dart';
import 'package:products_sdk/src/manager/application/foods/create/stocks/create_food_stocks_provider.dart';
import 'package:products_sdk/src/manager/application/foods/food_categories_provider.dart';
import 'package:products_sdk/src/manager/application/foods/foods_provider.dart';
import 'package:${package}/presentation/components/foods/editable_food_stock_item.dart';
import 'package:${package}/presentation/components/foods/extras_item.dart';

class CreateFoodStocksBody extends ConsumerStatefulWidget {
  const CreateFoodStocksBody({super.key});

  @override
  ConsumerState<CreateFoodStocksBody> createState() =>
      _CreateFoodStocksBodyState();
}

class _CreateFoodStocksBodyState extends ConsumerState<CreateFoodStocksBody> {
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(createFoodStocksProvider.notifier).setInitialStocks(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Consumer(
        builder: (context, ref, child) {
          final state = ref.watch(createFoodStocksProvider);
          final event = ref.read(createFoodStocksProvider.notifier);
          final foodsEvent = ref.read(foodsProvider.notifier);
          final categoriesState = ref.watch(foodCategoriesProvider);
          final detailsState = ref.watch(createFoodDetailsProvider);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              10.verticalSpace,
              SizedBox(
                height: 60.r,
                child: ListView.builder(
                  itemCount: state.groups.length,
                  scrollDirection: Axis.horizontal,
                  shrinkWrap: true,
                  padding: REdgeInsets.symmetric(horizontal: 16),
                  physics: const BouncingScrollPhysics(),
                  itemBuilder: (context, index) => ExtrasItem(
                    extras: state.groups[index],
                    onTap: () {
                      AppHelpers.showCustomModalBottomSheet(
                        paddingTop: MediaQuery.paddingOf(context).top + 150,
                        context: context,
                        radius: 12,
                        modal: CreateFoodEditExtrasModal(groupIndex: index),
                        isDarkMode: false,
                      );
                    },
                  ),
                ),
              ),
              Expanded(
                child: Form(
                  key: _formKey,
                  child: ListView.builder(
                    itemCount: state.stocks.length,
                    shrinkWrap: true,
                    padding:
                        REdgeInsets.symmetric(vertical: 10, horizontal: 16),
                    physics: const BouncingScrollPhysics(),
                    itemBuilder: (context, index) {
                      return EditableFoodStockItem(
                        key: UniqueKey(),
                        isDeletable: index != 0,
                        stock: state.stocks[index],
                        onDeleteStock: () => event.deleteStock(index),
                        onPriceChange: (value) =>
                            event.setPrice(value: value, index: index),
                        onQuantityChange: (value) =>
                            event.setQuantity(value: value, index: index),
                        onAddonTap: (context) =>
                            AppHelpers.showCustomModalBottomSheet(
                          paddingTop: MediaQuery.paddingOf(context).top + 150,
                          context: context,
                          radius: 12,
                          modal: CreateFoodAddonsModal(
                            stock: state.stocks[index],
                            onSave: (addons) =>
                                event.setStockAddons(addons, index),
                          ),
                          isDarkMode: true,
                        ),
                        onSkuChange: (value) {
                          event.setSku(value: value, index: index);
                        },
                      );
                    },
                  ),
                ),
              ),
              Padding(
                padding: REdgeInsets.symmetric(horizontal: 20),
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.save),
                  isLoading: state.isSaving,
                  onPressed: () {
                    if (_formKey.currentState?.validate() ?? false) {
                      event.updateStocks(
                        uuid: detailsState.createdProduct?.uuid,
                        updated: () {
                          foodsEvent.fetchProducts(
                            isRefresh: true,
                            categoryId: categoriesState.activeIndex == 1
                                ? null
                                : categoriesState
                                    .categories[categoriesState.activeIndex - 2]
                                    .id,
                          );
                          AppHelpers.showCheckTopSnackBarDone(
                            context,
                            AppHelpers.getTranslation(
                                TrKeys.successfullyUpdated),
                          );
                          context.maybePop();
                        },
                        failed: () => AppHelpers.showCheckTopSnackBar(
                          context,
                          AppHelpers.getTranslation(TrKeys.updateFailed),
                        ),
                      );
                    }
                  },
                ),
              ),
              20.verticalSpace,
            ],
          );
        },
      ),
    );
  }
}
