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

import 'package:${package}/presentation/theme/theme.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

class BottomNavigatorItem extends StatelessWidget {
  final VoidCallback selectItem;
  final int index;
  final int currentIndex;
  final IconData selectIcon;
  final IconData unSelectIcon;
  final bool isScrolling;

  const BottomNavigatorItem({
    super.key,
    required this.selectItem,
    required this.index,
    required this.selectIcon,
    required this.unSelectIcon,
    required this.currentIndex,
    required this.isScrolling,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: selectItem,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 700),
        color: AppStyle.transparent,
        height: isScrolling ? 0.h : 30.h,
        width: isScrolling ? 0.w : 56.w,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: index == currentIndex
                  ? Icon(
                      selectIcon,
                      size: isScrolling ? 0.r : 24.r,
                      color: AppStyle.white,
                    )
                  : Icon(
                      unSelectIcon,
                      size: isScrolling ? 0.r : 24.r,
                      color: AppStyle.white,
                    ),
            ),
            AnimatedContainer(
              height: isScrolling ? 0.h : 4.h,
              width: isScrolling ? 0.w : 24.w,
              decoration: BoxDecoration(
                color: index == currentIndex
                    ? AppStyle.primary
                    : AppStyle.transparent,
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(100.r),
                  topRight: Radius.circular(100.r),
                ),
              ),
              duration: const Duration(milliseconds: 400),
            )
          ],
        ),
      ),
    );
  }
}
