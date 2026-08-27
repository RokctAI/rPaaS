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
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/common/infrastructure/models/data/seller_stock.dart';
import 'package:products_sdk/src/manager/utils/seller_form_helpers.dart';
import 'package:base_sdk/src/presentation/components/text_fields/underlined_text_field.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';

class EditableFoodStockItem extends StatelessWidget {
  final SellerStock stock;
  final Function(String) onPriceChange;
  final Function(String) onQuantityChange;
  final Function(String) onSkuChange;
  final Function() onDeleteStock;
  final bool isDeletable;
  final Function(BuildContext) onAddonTap;

  const EditableFoodStockItem({
    super.key,
    required this.stock,
    required this.onPriceChange,
    required this.onQuantityChange,
    required this.onDeleteStock,
    required this.isDeletable,
    required this.onAddonTap,
    required this.onSkuChange,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppStyle.white,
        borderRadius: BorderRadius.circular(16.r),
      ),
      padding: REdgeInsets.symmetric(horizontal: 20, vertical: 16),
      margin: REdgeInsets.only(bottom: 8),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: UnderlinedTextField(
                  label: '${AppHelpers.getTranslation(TrKeys.price)}*',
                  inputType: TextInputType.number,
                  textInputAction: TextInputAction.next,
                  initialText: stock.price == null
                      ? ''
                      : stock.price.toString(),
                  onChanged: onPriceChange,
                  validator: SellerFormValidators.emptyCheck,
                ),
              ),
              10.horizontalSpace,
              Expanded(
                child: UnderlinedTextField(
                  label: '${AppHelpers.getTranslation(TrKeys.quantity)}*',
                  inputType: TextInputType.number,
                  textInputAction: TextInputAction.next,
                  initialText: stock.quantity == null
                      ? ''
                      : stock.quantity.toString(),
                  onChanged: onQuantityChange,
                  validator: SellerFormValidators.emptyCheck,
                ),
              ),
              if (isDeletable)
                ButtonsBouncingEffect(
                  child: GestureDetector(
                    onTap: onDeleteStock,
                    child: Container(
                      width: 36.r,
                      height: 36.r,
                      margin: REdgeInsets.only(left: 10),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(6.r),
                        color: AppStyle.bgGrey,
                      ),
                      alignment: Alignment.center,
                      child: Icon(Remix.delete_bin_line, size: 18.r),
                    ),
                  ),
                ),
            ],
          ),
          4.verticalSpace,
          UnderlinedTextField(
            label: AppHelpers.getTranslation(TrKeys.sku),
            textInputAction: TextInputAction.next,
            initialText: stock.sku == null ? '' : stock.sku.toString(),
            onChanged: onSkuChange,
          ),
          if (stock.extras != null && (stock.extras?.isNotEmpty ?? false))
            ListView.builder(
              shrinkWrap: true,
              itemCount: stock.extras?.length,
              physics: const NeverScrollableScrollPhysics(),
              padding: EdgeInsets.zero,
              itemBuilder: (context, index) {
                final extras = stock.extras?[index];
                return Padding(
                  padding: REdgeInsets.only(top: 16),
                  child: UnderlinedTextField(
                    label: '${extras?.group?.translation?.title}',
                    initialText: extras?.value,
                    readOnly: true,
                    validator: SellerFormValidators.emptyCheck,
                  ),
                );
              },
            ),
          UnderlinedTextField(
            label: '',
            initialText: AppHelpers.getTranslation(TrKeys.addons),
            readOnly: true,
            descriptionText: SellerAddonHelpers.selectedAddonsTitles(stock),
            onTap: () => onAddonTap(context),
            validator: SellerFormValidators.emptyCheck,
          ),
        ],
      ),
    );
  }
}
