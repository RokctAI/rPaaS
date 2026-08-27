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
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:intl/intl.dart' show toBeginningOfSentenceCase;

import 'package:base_sdk/src/models/data/shop_data.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

// Ported from paas_manager lib/presentation/component/list_items/
// small_weekday_item.dart. Only the restaurant vertical reads it, so it
// installs as a merchants component (lib/presentation/components/
// restaurant/) rather than surviving in the host's shared component pool.
// The day model is base_sdk's [ShopWorkingDay]; `intl` is a host dependency
// (templates compile in the host package).
class SmallWeekdayItem extends StatelessWidget {
  final bool isSelected;
  final ShopWorkingDay day;
  final int size;
  final int fontSize;
  final int borderRadius;

  const SmallWeekdayItem({
    super.key,
    required this.isSelected,
    required this.day,
    this.size = 40,
    this.fontSize = 14,
    this.borderRadius = 10,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: size.r,
      width: size.r,
      decoration: BoxDecoration(
        color: isSelected ? AppStyle.primary : AppStyle.white,
        borderRadius: BorderRadius.circular(borderRadius.r),
      ),
      alignment: Alignment.center,
      child: Text(
        '${toBeginningOfSentenceCase(day.day?.substring(0, 2))}',
        style: AppStyle.interNormal(
          size: fontSize.sp,
          color: AppStyle.blackColor,
        ),
      ),
    );
  }
}
