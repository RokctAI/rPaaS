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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'add_category_modal.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/manager/application/foods/create/details/category/add_food_categories_provider.dart';
import 'package:products_sdk/src/manager/application/foods/food_categories_provider.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';
import 'package:${package}/presentation/components/foods/food_category_item.dart';

class FoodCategoriesModal extends ConsumerStatefulWidget {
  final bool isSubCategory;

  const FoodCategoriesModal({super.key, this.isSubCategory = false});

  @override
  ConsumerState<FoodCategoriesModal> createState() =>
      _FoodCategoriesModalState();
}

class _FoodCategoriesModalState extends ConsumerState<FoodCategoriesModal> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.isSubCategory) {
        ref.read(addFoodCategoriesProvider.notifier).updateCategoriesSub();
      }
      ref
          .read(addFoodCategoriesProvider.notifier)
          .setCategories(ref.watch(foodCategoriesProvider).categories);
    });
  }

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: Column(
        children: [
          const ModalDrag(),
          if (!widget.isSubCategory)
            GestureDetector(
              onTap: () => AppHelpers.showCustomModalBottomSheet(
                context: context,
                paddingTop: 100,
                modal: const AddCategoryModal(),
                isDarkMode: false,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Remix.play_list_add_line,
                    color: AppStyle.blue,
                    size: 18.r,
                  ),
                  10.horizontalSpace,
                  Text(
                    AppHelpers.getTranslation(TrKeys.addNewCategory),
                    style: AppStyle.interSemi(
                      size: 14,
                      color: AppStyle.blue,
                      letterSpacing: -0.3,
                    ),
                  ),
                ],
              ),
            ),
          16.verticalSpace,
          Divider(
            color: AppStyle.orderStatusProgressBack,
            height: 1.r,
            thickness: 1.r,
          ),
          24.verticalSpace,
          Expanded(
            child: Padding(
              padding: REdgeInsets.symmetric(horizontal: 16),
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Column(
                  children: [
                    TitleAndIcon(
                      title: AppHelpers.getTranslation(TrKeys.categories),
                      titleSize: 16,
                    ),
                    Consumer(
                      builder: (context, ref, child) {
                        final state = ref.watch(addFoodCategoriesProvider);
                        return ListView.builder(
                          physics: const NeverScrollableScrollPhysics(),
                          padding: EdgeInsets.zero,
                          shrinkWrap: true,
                          itemCount: widget.isSubCategory
                              ? state.categoriesSub.length
                              : state.categories.length,
                          itemBuilder: (context, index) {
                            return FoodCategoryItem(
                              category: widget.isSubCategory
                                  ? state.categoriesSub[index]
                                  : state.categories[index],
                              onTap: () {
                                widget.isSubCategory
                                    ? ref
                                          .read(
                                            addFoodCategoriesProvider.notifier,
                                          )
                                          .setActiveIndexSub(index)
                                    : ref
                                          .read(
                                            addFoodCategoriesProvider.notifier,
                                          )
                                          .setActiveIndex(index);
                                Navigator.pop(context);
                              },
                              isSelected:
                                  (widget.isSubCategory
                                      ? state.activeSubIndex
                                      : state.activeIndex) ==
                                  index,
                              onDelete:
                                  (widget.isSubCategory
                                          ? state.categoriesSub[index].shopId
                                          : state.categories[index].shopId) ==
                                      // Shop ids are shop_name docname
                                      // strings, never ints.
                                      LocalStorage.getShopJson()?['id']
                                          ?.toString()
                                  ? () {
                                      ref
                                          .read(
                                            addFoodCategoriesProvider.notifier,
                                          )
                                          .deleteCategories(
                                            state.categories[index],
                                          );
                                    }
                                  : null,
                            );
                          },
                        );
                      },
                    ),
                    20.verticalSpace,
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
