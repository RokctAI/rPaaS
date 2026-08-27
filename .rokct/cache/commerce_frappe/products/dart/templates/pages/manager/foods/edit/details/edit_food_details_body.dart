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

import 'edit_food_units_modal.dart';
import 'edit_food_categories_modal.dart';
import '../../widgets/food_kitchens_modal.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/models/data/translation.dart';
import 'package:kitchen_sdk/src/common/infrastructure/models/data/kitchen_data.dart';
import 'package:kitchen_sdk/src/manager/application/kitchens/kitchen_picker_provider.dart';
import 'package:products_sdk/src/manager/application/foods/edit/details/category/edit_food_categories_provider.dart';
import 'package:products_sdk/src/manager/application/foods/edit/details/edit_food_details_provider.dart';
import 'package:products_sdk/src/manager/application/foods/edit/details/units/edit_food_units_provider.dart';
import 'package:products_sdk/src/manager/application/foods/foods_provider.dart';
import 'package:products_sdk/src/manager/utils/seller_form_helpers.dart';
import 'package:base_sdk/src/presentation/components/custom_toggle3.dart';
import 'package:base_sdk/src/presentation/components/text_fields/underlined_text_field.dart';
import 'package:${package}/presentation/components/foods/multi_image_picker.dart';

/// Seeds kitchen_sdk's autoDispose picker here (not at the list-tap that
/// opened this modal): this body's `watch` keeps the provider alive for the
/// whole edit session, and the seed converts products_sdk's minimal
/// `SellerProductKitchen` into kitchen_sdk's `KitchenModel` at this
/// host-template boundary — exactly the conversion ADR-005 assigns to the
/// host.
class EditFoodDetailsBody extends ConsumerStatefulWidget {
  final Function() onSave;
  final ScrollController controller;

  const EditFoodDetailsBody({
    super.key,
    required this.onSave,
    required this.controller,
  });

  @override
  ConsumerState<EditFoodDetailsBody> createState() =>
      _EditFoodDetailsBodyState();
}

class _EditFoodDetailsBodyState extends ConsumerState<EditFoodDetailsBody> {
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final kitchen = ref.read(editFoodDetailsProvider).product?.kitchen;
      if (kitchen != null) {
        ref
            .read(kitchenPickerProvider.notifier)
            .initialise(
              selected: KitchenModel(
                id: kitchen.id,
                translation: Translation(title: kitchen.title),
              ),
            );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Padding(
        padding: REdgeInsets.symmetric(horizontal: 16),
        child: SingleChildScrollView(
          controller: widget.controller,
          physics: const BouncingScrollPhysics(),
          child: Consumer(
            builder: (context, ref, child) {
              final state = ref.watch(editFoodDetailsProvider);
              final categoryState = ref.watch(editFoodCategoriesProvider);
              final unitState = ref.watch(editFoodUnitsProvider);
              final kitchenState = ref.watch(kitchenPickerProvider);
              final event = ref.read(editFoodDetailsProvider.notifier);
              final foodsEvent = ref.read(foodsProvider.notifier);
              return state.product == null
                  ? Center(
                      child: CircularProgressIndicator(
                        strokeWidth: 3.r,
                        color: AppStyle.primary,
                      ),
                    )
                  : Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          24.verticalSpace,
                          state.isLoading
                              ? const Loading()
                              : MultiImagePicker(
                                  imageUrls: state.listOfUrls,
                                  listOfImages: state.images,
                                  onImageChange: event.setImageFile,
                                  onDelete: event.deleteImage,
                                ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            label:
                                '${AppHelpers.getTranslation(TrKeys.productTitle)}*',
                            inputType: TextInputType.text,
                            textCapitalization: TextCapitalization.sentences,
                            textInputAction: TextInputAction.next,
                            onChanged: event.setTitle,
                            initialText: state.product?.translation?.title,
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            label:
                                '${AppHelpers.getTranslation(TrKeys.description)}*',
                            inputType: TextInputType.text,
                            textCapitalization: TextCapitalization.sentences,
                            textInputAction: TextInputAction.next,
                            onChanged: event.setDescription,
                            initialText:
                                state.product?.translation?.description,
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            textController: categoryState.categoriesController,
                            label:
                                '${AppHelpers.getTranslation(TrKeys.productCategory)}*',
                            suffixIcon: Icon(
                              Remix.arrow_down_s_line,
                              color: AppStyle.blackColor,
                              size: 18.r,
                            ),
                            readOnly: true,
                            onTap: () => AppHelpers.showCustomModalBottomSheet(
                              paddingTop:
                                  MediaQuery.paddingOf(context).top + 100.h,
                              context: context,
                              modal: const EditFoodCategoriesModal(),
                              isDarkMode: false,
                            ),
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            textController: unitState.unitController,
                            label:
                                '${AppHelpers.getTranslation(TrKeys.units)}*',
                            suffixIcon: Icon(
                              Remix.arrow_down_s_line,
                              color: AppStyle.blackColor,
                              size: 18.r,
                            ),
                            readOnly: true,
                            onTap: () => AppHelpers.showCustomModalBottomSheet(
                              paddingTop:
                                  MediaQuery.paddingOf(context).top + 250.h,
                              context: context,
                              modal: const EditFoodUnitsModal(),
                              isDarkMode: false,
                            ),
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            textController: kitchenState.kitchenController,
                            label: AppHelpers.getTranslation(TrKeys.kitchen),
                            suffixIcon: Icon(
                              Remix.arrow_down_s_line,
                              color: AppStyle.blackColor,
                              size: 18.r,
                            ),
                            readOnly: true,
                            onTap: () => AppHelpers.showCustomModalBottomSheet(
                              paddingTop:
                                  MediaQuery.paddingOf(context).top + 250.h,
                              context: context,
                              modal: const FoodKitchensModal(),
                              isDarkMode: false,
                            ),
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            label:
                                '${AppHelpers.getTranslation(TrKeys.interval)}*',
                            inputType: TextInputType.number,
                            textCapitalization: TextCapitalization.sentences,
                            textInputAction: TextInputAction.next,
                            onChanged: event.setInterval,
                            initialText: (state.product?.interval ?? 1)
                                .toString(),
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: UnderlinedTextField(
                                  label:
                                      '${AppHelpers.getTranslation(TrKeys.minQuantity)}*',
                                  inputType: TextInputType.number,
                                  textInputAction: TextInputAction.next,
                                  initialText:
                                      state.product?.minQty.toString() ?? '',
                                  onChanged: event.setMinQty,
                                  validator: SellerFormValidators.emptyCheck,
                                ),
                              ),
                              10.horizontalSpace,
                              Expanded(
                                child: UnderlinedTextField(
                                  label:
                                      '${AppHelpers.getTranslation(TrKeys.maxQuantity)}*',
                                  inputType: TextInputType.number,
                                  textInputAction: TextInputAction.next,
                                  initialText:
                                      state.product?.maxQty.toString() ?? '',
                                  onChanged: event.setMaxQty,
                                  validator: (value) =>
                                      SellerFormValidators.maxQtyCheck(
                                        value,
                                        state.minQty,
                                      ),
                                ),
                              ),
                            ],
                          ),
                          24.verticalSpace,
                          UnderlinedTextField(
                            label: '${AppHelpers.getTranslation(TrKeys.tax)}*',
                            inputType: TextInputType.number,
                            textInputAction: TextInputAction.next,
                            initialText: state.tax,
                            onChanged: event.setTax,
                            validator: SellerFormValidators.emptyCheck,
                          ),
                          24.verticalSpace,
                          // Manager-only: cost price (optional). Never
                          // rendered on customer-facing surfaces — this
                          // template only installs under app_type=manager.
                          UnderlinedTextField(
                            label: AppHelpers.getTranslation(TrKeys.costPrice),
                            inputType: TextInputType.number,
                            textInputAction: TextInputAction.next,
                            initialText: state.costPrice,
                            onChanged: event.setCostPrice,
                          ),
                          24.verticalSpace,
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                AppHelpers.getTranslation(TrKeys.showProduct),
                                style: AppStyle.interNormal(
                                  size: 14.sp,
                                  letterSpacing: -0.3,
                                  color: AppStyle.blackColor,
                                ),
                              ),
                              CustomToggle(
                                controller: ValueNotifier<bool>(state.active),
                                onChange: event.setActive,
                              ),
                            ],
                          ),
                          24.verticalSpace,
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                AppHelpers.getTranslation(TrKeys.adultsOnly),
                                style: AppStyle.interNormal(
                                  size: 14.sp,
                                  letterSpacing: -0.3,
                                  color: AppStyle.blackColor,
                                ),
                              ),
                              CustomToggle(
                                controller: ValueNotifier<bool>(state.isAdult),
                                onChange: event.setIsAdult,
                              ),
                            ],
                          ),
                          40.verticalSpace,
                          CustomButton(
                            title: AppHelpers.getTranslation(TrKeys.save),
                            isLoading: state.isLoading,
                            onPressed: () {
                              if (_formKey.currentState?.validate() ?? false) {
                                event.updateProduct(
                                  unit: unitState.foodUnit,
                                  kitchenId: kitchenState.selected?.id,
                                  category: categoryState.foodCategory,
                                  updated: (product) {
                                    widget.onSave();
                                    AppHelpers.showCheckTopSnackBarDone(
                                      context,
                                      AppHelpers.getTranslation(
                                        TrKeys.successfullyUpdated,
                                      ),
                                    );
                                    foodsEvent.updateSingleProduct(product);
                                  },
                                  failed: () => AppHelpers.showCheckTopSnackBar(
                                    context,
                                    AppHelpers.getTranslation(
                                      TrKeys.updateFailed,
                                    ),
                                  ),
                                );
                              }
                            },
                          ),
                          20.verticalSpace,
                        ],
                      ),
                    );
            },
          ),
        ),
      ),
    );
  }
}
