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
import 'package:products_sdk/src/common/infrastructure/models/data/seller_product_data.dart';

class SelectableAddonItem extends StatelessWidget {
  final SellerProductData addon;
  final bool isLast;
  final VoidCallback? onTap;

  const SelectableAddonItem({
    super.key,
    required this.addon,
    this.isLast = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          18.verticalSpace,
          Row(
            children: [
              Icon(
                (addon.isSelectedAddon ?? false)
                    ? Remix.checkbox_circle_fill
                    : Remix.checkbox_blank_circle_line,
                size: 24.r,
                color: (addon.isSelectedAddon ?? false)
                    ? AppStyle.primary
                    : AppStyle.blackColor,
              ),
              14.horizontalSpace,
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${addon.translation?.title}',
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        letterSpacing: -0.3,
                      ),
                    ),
                    4.verticalSpace,
                    Text(
                      '${addon.translation?.description}',
                      style: AppStyle.interRegular(
                        size: 12.sp,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          20.verticalSpace,
          if (!isLast)
            Divider(
              thickness: 1.r,
              height: 1.r,
              color: AppStyle.textGrey.withOpacity(0.15),
            ),
        ],
      ),
    );
  }
}
