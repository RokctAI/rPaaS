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

import 'dart:io';
import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:shimmer/shimmer.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';

class ShopAvatar extends StatelessWidget {
  final double size;
  final double padding;
  final double radius;
  final Color bgColor;
  final String? imageUrl;
  final String? path;

  const ShopAvatar({
    super.key,
    required this.size,
    required this.padding,
    this.bgColor = const Color(0x06000000),
    this.radius = 10,
    this.imageUrl,
    this.path,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius.r),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
        child: Container(
          width: size.r,
          height: size.r,
          color: bgColor,
          padding: EdgeInsets.all(padding.r),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(size.r / 2),
            child: imageUrl != null
                ? CachedNetworkImage(
                    imageUrl: '$imageUrl',
                    fit: BoxFit.cover,
                    progressIndicatorBuilder: (context, url, progress) {
                      return Shimmer.fromColors(
                        baseColor: AppStyle.shimmerBase,
                        highlightColor: AppStyle.shimmerHighlight,
                        child: Container(
                          height: size.r,
                          decoration: BoxDecoration(
                            color: AppStyle.white,
                            borderRadius: BorderRadius.circular(size.r / 2),
                          ),
                        ),
                      );
                    },
                    errorWidget: (context, url, error) {
                      return Container(
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppStyle.bgGrey,
                        ),
                        alignment: Alignment.center,
                        child: const Icon(
                          Remix.image_line,
                          color: AppStyle.black,
                        ),
                      );
                    },
                  )
                : path != null
                ? Image.file(
                    File(path!),
                    width: size.r,
                    height: size.r,
                    fit: BoxFit.cover,
                  )
                : null,
          ),
        ),
      ),
    );
  }
}
