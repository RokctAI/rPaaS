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
import 'package:base_sdk/src/presentation/theme/app_style.dart';

class StatisticsItem extends StatelessWidget {
  final String title;
  final String count;
  final String percentage;
  final Color bgColor;
  final Color textColor;
  final Color iconColor;

  const StatisticsItem(
      {super.key,
      required this.title,
      required this.count,
      required this.percentage,
      required this.bgColor,
      required this.textColor,
      required this.iconColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 88.h,
      width: (MediaQuery.sizeOf(context).width - 140.w) / 2,
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10.r),
      ),
      padding: EdgeInsets.all(12.r),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppStyle.interNormal(
                size: 12, color: textColor, letterSpacing: -0.3),
          ),
          const Spacer(),
          Row(
            children: [
              Text(
                count,
                style: AppStyle.interSemi(
                    size: 14, color: textColor, letterSpacing: -0.6),
              ),
              Container(
                width: 6.r,
                height: 6.r,
                margin: EdgeInsets.symmetric(horizontal: 4.w),
                decoration:
                    BoxDecoration(shape: BoxShape.circle, color: iconColor),
              ),
              Text(
                percentage,
                style: AppStyle.interSemi(
                    size: 14, color: textColor, letterSpacing: -0.6),
              ),
            ],
          )
        ],
      ),
    );
  }
}
