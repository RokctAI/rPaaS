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
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:orders_sdk/src/manager/infrastructure/models/models.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';
import 'package:${package}/presentation/components/orders/food_item.dart';
import 'package:${package}/presentation/components/orders/order_food_item.dart';

class ProductsBody extends StatelessWidget {
  final RefreshController refreshController;
  final int bottomPadding;
  final bool isLoading;
  final int itemSpacing;
  final List<ProductData> products;
  final Function(int) onProductTap;
  final Function() onLoading;
  final Function() onRefreshing;
  final bool isOrderFoods;
  final int loadingHeight;
  final ScrollPhysics scrollPhysics;

  const ProductsBody({
    super.key,
    required this.refreshController,
    required this.isLoading,
    required this.products,
    required this.onProductTap,
    required this.onLoading,
    required this.onRefreshing,
    this.itemSpacing = 1,
    this.bottomPadding = 72,
    this.isOrderFoods = false,
    this.loadingHeight = 188,
    this.scrollPhysics = const BouncingScrollPhysics(),
  });

  @override
  Widget build(BuildContext context) {
    return isLoading
        ? LoadingList(
            verticalPadding: 16,
            itemBorderRadius: 0,
            itemPadding: itemSpacing,
            itemHeight: loadingHeight,
          )
        : SmartRefresher(
            controller: refreshController,
            physics: scrollPhysics,
            enablePullDown: true,
            enablePullUp: true,
            onLoading: onLoading,
            onRefresh: onRefreshing,
            child: ListView.builder(
              physics: const NeverScrollableScrollPhysics(),
              padding: REdgeInsets.only(top: 16, bottom: bottomPadding.r),
              shrinkWrap: true,
              itemCount: products.length,
              itemBuilder: (context, index) => isOrderFoods
                  ? OrderFoodItem(
                      product: products[index],
                      onTap: () => onProductTap(index),
                      spacing: itemSpacing,
                    )
                  : FoodItem(
                      product: products[index],
                      spacing: itemSpacing,
                      onTap: () => onProductTap(index),
                    ),
            ),
          );
  }
}
