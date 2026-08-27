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

import 'stocks/create_food_stocks_body.dart';
import 'details/create_food_details_body.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/manager/application/foods/create/details/create_food_details_provider.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';

/// Opened by the merchants_sdk home shell's FAB when the foods tab is on
/// "foods" — `CreateProductModal` at this install path is main_page.dart's
/// import contract.
class CreateProductModal extends ConsumerStatefulWidget {
  const CreateProductModal({super.key});

  @override
  ConsumerState<CreateProductModal> createState() => _CreateProductModalState();
}

class _CreateProductModalState extends ConsumerState<CreateProductModal>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(createFoodDetailsProvider.notifier).updateAddFoodInfo(),
    );
  }

  @override
  void dispose() {
    super.dispose();
    _tabController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: Column(
        children: [
          const ModalDrag(),
          IgnorePointer(
            child: Container(
              padding: REdgeInsets.all(6),
              height: 48.h,
              decoration: BoxDecoration(
                color: AppStyle.transparent,
                borderRadius: BorderRadius.circular(10.r),
                border: Border.all(color: AppStyle.tabBarBorderColor),
              ),
              margin: REdgeInsets.symmetric(horizontal: 16),
              child: TabBar(
                onTap: (index) {},
                controller: _tabController,
                indicator: BoxDecoration(
                  borderRadius: BorderRadius.circular(10.r),
                  color: AppStyle.blackColor,
                ),
                labelColor: AppStyle.white,
                unselectedLabelColor: AppStyle.textGrey,
                unselectedLabelStyle: AppStyle.interRegular(size: 14.sp),
                labelStyle: AppStyle.interSemi(size: 14.sp),
                tabs: [
                  Tab(
                    child: Text(AppHelpers.getTranslation(TrKeys.addProduct)),
                  ),
                  Tab(
                    child: Text(AppHelpers.getTranslation(TrKeys.stocks)),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                CreateFoodDetailsBody(
                  onSave: () => _tabController.animateTo(
                    1,
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeIn,
                  ),
                ),
                const CreateFoodStocksBody(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
