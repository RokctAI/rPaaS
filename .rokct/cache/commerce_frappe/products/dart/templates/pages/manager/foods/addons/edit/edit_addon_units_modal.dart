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

import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/manager/application/addons/edit/units/edit_addon_units_provider.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';
import 'package:${package}/presentation/components/foods/food_unit_item.dart';

class EditAddonUnitsModal extends ConsumerStatefulWidget {
  const EditAddonUnitsModal({super.key});

  @override
  ConsumerState<EditAddonUnitsModal> createState() =>
      _EditAddonUnitsModalState();
}

class _EditAddonUnitsModalState extends ConsumerState<EditAddonUnitsModal> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(editAddonUnitsProvider.notifier).fetchUnits(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: Padding(
        padding: REdgeInsets.symmetric(horizontal: 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const ModalDrag(),
            TitleAndIcon(
              title: AppHelpers.getTranslation(TrKeys.units),
              titleSize: 16,
            ),
            24.verticalSpace,
            Consumer(
              builder: (context, ref, child) {
                final state = ref.watch(editAddonUnitsProvider);
                final event = ref.read(editAddonUnitsProvider.notifier);
                return state.isLoading
                    ? Center(
                        child: CircularProgressIndicator(
                          strokeWidth: 3.r,
                          color: AppStyle.primary,
                        ),
                      )
                    : Expanded(
                        child: ListView.builder(
                          padding: EdgeInsets.zero,
                          itemCount: state.units.length,
                          shrinkWrap: true,
                          itemBuilder: (context, index) => FoodUnitItem(
                            unit: state.units[index],
                            onTap: () => event.setActiveIndex(index),
                            isSelected: state.activeIndex == index,
                          ),
                        ),
                      );
              },
            ),
            24.verticalSpace,
            CustomButton(
              title: AppHelpers.getTranslation(TrKeys.close),
              onPressed: context.maybePop,
            ),
            20.verticalSpace,
          ],
        ),
      ),
    );
  }
}
