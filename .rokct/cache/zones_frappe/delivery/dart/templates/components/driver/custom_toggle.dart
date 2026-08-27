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
import 'package:flutter_advanced_switch/flutter_advanced_switch.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class CustomToggle extends StatefulWidget {
  final bool isOnline;
  final ValueChanged<bool> onChange;
  final bool isOrder;

  const CustomToggle(
      {super.key,
      required this.isOnline,
      required this.onChange,
      this.isOrder = false});

  @override
  State<CustomToggle> createState() => _CustomToggleState();
}

class _CustomToggleState extends State<CustomToggle> {
  var controller = ValueNotifier<bool>(false);

  @override
  void initState() {
    controller = ValueNotifier<bool>(widget.isOnline);
    controller.addListener(() {
      widget.onChange(controller.value);
    });
    super.initState();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AdvancedSwitch(
      controller: controller,
      initialValue: controller.value,
      activeColor: AppStyle.primary,
      inactiveColor: AppStyle.orderStatusProgressBack,
      borderRadius: BorderRadius.circular(10.r),
      width: widget.isOrder ? 70.w : 94.w,
      height: widget.isOrder ? 32.w : 40.h,
      enabled: true,
      disabledOpacity: 0.5,
      thumb: Container(
        margin: EdgeInsets.all(widget.isOrder ? 2.r : 4.r),
        padding: EdgeInsets.symmetric(
          vertical: 6.h,
        ),
        decoration: BoxDecoration(
          color: AppStyle.white,
          borderRadius: BorderRadius.circular(10.r),
          boxShadow: [
            BoxShadow(
              color: Color(0xFF6B6B6B).withOpacity(0.4),
              spreadRadius: 0,
              blurRadius: 2,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              height: double.infinity,
              width: 3.r,
              color: AppStyle.orderStatusProgressBack,
            ),
            2.horizontalSpace,
            Container(
              height: double.infinity,
              width: 3.r,
              color: AppStyle.orderStatusProgressBack,
            )
          ],
        ),
      ),
      activeChild: Text(
        !widget.isOrder
            ? AppHelpers.getTranslation(TrKeys.online)
            : AppHelpers.getTranslation(TrKeys.active),
        style: AppStyle.interNormal(
          size: widget.isOrder ? 10.sp : 12.sp,
          letterSpacing: -0.3,
          color: AppStyle.black,
        ),
      ),
      inactiveChild: Text(
        !widget.isOrder
            ? AppHelpers.getTranslation(TrKeys.offline)
            : AppHelpers.getTranslation(TrKeys.inActive),
        style: AppStyle.interNormal(
          size: widget.isOrder ? 10.sp : 12.sp,
          letterSpacing: -0.3,
          color: AppStyle.black,
        ),
      ),
    );
  }
}
