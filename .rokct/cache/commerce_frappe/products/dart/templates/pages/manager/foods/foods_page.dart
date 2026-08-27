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
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'foods/foods_body.dart';
import 'extras/extras_body.dart';
import 'addons/addons_body.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/text_fields/search_text_field.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:merchants_sdk/src/manager/application/main/main_provider.dart';
import 'package:products_sdk/src/manager/application/addons/addons_provider.dart';
import 'package:products_sdk/src/manager/application/extras/extras_provider.dart';
import 'package:products_sdk/src/manager/application/foods/food_categories_provider.dart';
import 'package:products_sdk/src/manager/application/foods/food_tabs_provider.dart';
import 'package:products_sdk/src/manager/application/foods/foods_provider.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';

/// The foods tab of the manager home shell (merchants_sdk's main_page.dart
/// hosts it at index 1 — this install path is that shell's import contract).
/// Tab-hosted, so no route. The legacy filter icon kept its no-op tap: the
/// app's FoodsFilterModal and foodsFilterProvider were dead code (never
/// opened, repository calls commented out) and were not ported.
class FoodsPage extends ConsumerStatefulWidget {
  const FoodsPage({super.key});

  @override
  ConsumerState<FoodsPage> createState() => _FoodsPageState();
}

class _FoodsPageState extends ConsumerState<FoodsPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  late ScrollController _scrollController;
  late RefreshController _categoryController;
  late RefreshController _productController;
  late RefreshController _addonsController;
  late RefreshController _extrasController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        switch (_tabController.index) {
          case 0:
            ref.read(foodTabsProvider.notifier).setSelectedIndex(0);
            break;
          case 1:
            ref.read(foodTabsProvider.notifier).setSelectedIndex(1);
            break;
          case 2:
            ref.read(foodTabsProvider.notifier).setSelectedIndex(2);
            break;
          default:
            ref.read(foodTabsProvider.notifier).setSelectedIndex(0);
            break;
        }
      }
    });
    _scrollController = ScrollController();
    _categoryController = RefreshController();
    _productController = RefreshController();
    _addonsController = RefreshController();
    _extrasController = RefreshController();
    _scrollController.addListener(() {
      final direction = _scrollController.position.userScrollDirection;
      if (direction == ScrollDirection.reverse) {
        ref.read(mainProvider.notifier).changeScrolling(true);
      } else {
        ref.read(mainProvider.notifier).changeScrolling(false);
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(foodCategoriesProvider.notifier).initialFetchCategories();
      ref.read(foodsProvider.notifier).initialFetchFoods();
      ref.read(addonsProvider.notifier).initialFetchAddons();
      ref.read(extrasProvider.notifier).fetchGroups();
    });
  }

  @override
  void dispose() {
    super.dispose();
    _tabController.dispose();
    _scrollController.dispose();
    _categoryController.dispose();
    _productController.dispose();
    _addonsController.dispose();
    _extrasController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Scaffold(
        backgroundColor: AppStyle.bgGrey,
        body: Column(
          children: [
            CustomAppBar(
              bottomPadding: 4.h,
              child: Consumer(
                builder: (context, ref, child) {
                  final foodsEvent = ref.read(foodsProvider.notifier);
                  final categoriesState = ref.watch(foodCategoriesProvider);
                  return SearchTextField(
                    bgColor: AppStyle.transparent,
                    onChanged: (value) => foodsEvent.setQuery(
                      query: value,
                      categoryId: categoriesState.activeIndex == 1
                          ? null
                          : categoriesState
                                .categories[categoriesState.activeIndex - 2]
                                .id,
                    ),
                    suffixIcon: ButtonsBouncingEffect(
                      child: GestureDetector(
                        onTap: () {},
                        child: Icon(
                          Remix.equalizer_fill,
                          color: AppStyle.blackColor,
                          size: 20.r,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            Expanded(
              child: NestedScrollView(
                controller: _scrollController,
                headerSliverBuilder:
                    (BuildContext context, bool innerBoxIsScrolled) {
                      return [
                        SliverAppBar(
                          floating: true,
                          backgroundColor: AppStyle.transparent,
                          elevation: 0,
                          titleSpacing: 0,
                          toolbarHeight: 48.h,
                          title: Container(
                            padding: REdgeInsets.all(6),
                            margin: REdgeInsets.symmetric(horizontal: 16),
                            height: 48.h,
                            decoration: BoxDecoration(
                              color: AppStyle.transparent,
                              borderRadius: BorderRadius.circular(10.r),
                              border: Border.all(
                                color: AppStyle.tabBarBorderColor,
                              ),
                            ),
                            child: TabBar(
                              onTap: (index) {},
                              controller: _tabController,
                              indicator: BoxDecoration(
                                borderRadius: BorderRadius.circular(10.r),
                                color: AppStyle.blackColor,
                              ),
                              labelColor: AppStyle.white,
                              unselectedLabelColor: AppStyle.textGrey,
                              unselectedLabelStyle: AppStyle.interRegular(
                                size: 14.sp,
                              ),
                              labelStyle: AppStyle.interSemi(size: 14.sp),
                              tabs: [
                                Tab(
                                  child: Text(
                                    AppHelpers.getTranslation(TrKeys.foods),
                                  ),
                                ),
                                Tab(
                                  child: Text(
                                    AppHelpers.getTranslation(TrKeys.addons),
                                  ),
                                ),
                                Tab(
                                  child: Text(
                                    AppHelpers.getTranslation(TrKeys.extras),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ];
                    },
                body: TabBarView(
                  physics: const BouncingScrollPhysics(),
                  controller: _tabController,
                  children: [
                    FoodsBody(
                      categoryController: _categoryController,
                      productController: _productController,
                    ),
                    AddonsBody(addonsController: _addonsController),
                    ExtrasBody(refreshController: _extrasController),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
