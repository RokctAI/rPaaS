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
import 'package:base_sdk/src/presentation/components/helper/common_image.dart';

class DriverAvatar extends StatelessWidget {
  final String? imageUrl;
  final num? rate;

  const DriverAvatar({super.key, this.imageUrl, required this.rate});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 70.r,
      child: Stack(
        children: [
          Container(
            height: 50.r,
            width: 50.r,
            decoration: const BoxDecoration(
              color: AppStyle.white,
              shape: BoxShape.circle,
            ),
            padding: REdgeInsets.all(2),
            child: ClipOval(child: CommonImage(url: imageUrl)),
          ),
          Positioned(
            top: 40.h,
            left: 2.w,
            child: Container(
              decoration: BoxDecoration(
                color: AppStyle.pendingDark,
                borderRadius: BorderRadius.circular(10.r),
                border: Border.all(color: AppStyle.white, width: 2),
              ),
              padding: EdgeInsets.symmetric(vertical: 4.h, horizontal: 6.w),
              child: Row(
                children: [
                  Icon(
                    Remix.star_smile_fill,
                    color: AppStyle.white,
                    size: 12.r,
                  ),
                  Text(
                    double.parse((rate ?? 0.0).toString()).toStringAsFixed(2),
                    style: AppStyle.interNormal(
                      size: 10.sp,
                      color: AppStyle.white,
                      letterSpacing: -0.26,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
