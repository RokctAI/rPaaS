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
import 'package:flutter_svg/svg.dart';
import 'package:${package}/presentation/pages/profile/courier_statistics_provider.dart';

import 'package:base_sdk/src/navigation/embedded_widgets.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/home/widgets/stores.dart';
import 'package:base_sdk/src/services/app_assets.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class BottomSheetScreen extends StatefulWidget {
  final bool isScrolling;

  const BottomSheetScreen({super.key, required this.isScrolling});

  @override
  State<BottomSheetScreen> createState() => _BottomSheetScreenState();
}

class _BottomSheetScreenState extends State<BottomSheetScreen> {
  final List<String> image = [
    "https://www.deliveryhero.com/wp-content/uploads/2021/01/TAR_5922.jpg",
    'https://images.ctfassets.net/trvmqu12jq2l/1LFP1rAaPMiEx5y11ZZv2F/5167948e81a58a08e516631e07ee154c/blog-hero-1208x1080-v115.14.01.jpg',
    'https://images.unsplash.com/photo-1566576721346-d4a3b4eaeb55?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8cGFja2FnZSUyMGRlbGl2ZXJ5fGVufDB8fDB8fA%3D%3D&w=1000&q=80',
  ];

  @override
  Widget build(BuildContext context) {
    return AnimatedPositioned(
      bottom: widget.isScrolling ? -280.h : 0,
      duration: const Duration(milliseconds: 400),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [_weatherWarningsBanner(), _sheetBody(context)],
      ),
    );
  }

  /// Severe-weather heads-up banner for the courier, rendered through the
  /// cross-SDK embedded-widgets seam (ADR-005): weather_sdk declares the
  /// zero-arg `weatherWarningsBanner` method in its manifest's
  /// `embedded_widgets` list and the installer injects the implementation
  /// into the host's `_HostEmbeddedWidgets`, so this file never imports
  /// weather_sdk.
  ///
  /// The call is dispatched dynamically and guarded because weather_sdk is
  /// OPTIONAL in courier compositions: without it the host has no
  /// `weatherWarningsBanner` implementation (base_sdk's [EmbeddedWidgets]
  /// interface does not declare the method either) and `EmbeddedWidgets.I`
  /// answers through `noSuchMethod` with a StateError - the courier home
  /// must then render nothing extra and never crash. When weather_sdk IS
  /// composed, the banner itself renders `SizedBox.shrink()` unless there
  /// is an active notice, so in the calm case this adds zero layout either
  /// way.
  ///
  /// Docked above the sheet card (not inside it) because the card's height
  /// is fixed at 336.h - a variable-height notice inside it would overflow.
  Widget _weatherWarningsBanner() {
    Widget? banner;
    try {
      final dynamic embedded = EmbeddedWidgets.I;
      final dynamic built = embedded.weatherWarningsBanner();
      if (built is Widget) banner = built;
    } catch (_) {
      // weather_sdk not composed into this app: show nothing.
    }
    if (banner == null) return const SizedBox.shrink();
    return Padding(
      padding: EdgeInsets.only(left: 16.w, right: 16.w, bottom: 8.h),
      child: banner,
    );
  }

  Widget _sheetBody(BuildContext context) {
    return Container(
      height: 336.h,
      width: MediaQuery.sizeOf(context).width,
      decoration: BoxDecoration(
        color: AppStyle.bgGrey,
        borderRadius: BorderRadius.only(
          topRight: Radius.circular(12.r),
          topLeft: Radius.circular(12.r),
        ),
        boxShadow: [
          BoxShadow(
            color: AppStyle.black.withOpacity(0.25),
            blurRadius: 40,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      padding: EdgeInsets.only(
        top: 8.h,
        bottom: MediaQuery.paddingOf(context).bottom + 16.h,
        left: 16.w,
        right: 16.w,
      ),
      child: Column(
        children: [
          Container(
            height: 4.h,
            width: 48.w,
            decoration: BoxDecoration(
              color: AppStyle.dragElement,
              borderRadius: BorderRadius.circular(40.r),
            ),
          ),
          Column(
            children: [
              18.verticalSpace,
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [_balance(context), _benefit(context)],
              ),
              SizedBox(
                height: 186.h,
                child: ListView.builder(
                  padding: EdgeInsets.only(top: 24.h),
                  scrollDirection: Axis.horizontal,
                  itemCount: image.length,
                  itemBuilder: (context, index) {
                    return StoresPage(image: image[index]);
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _benefit(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // context.pushRoute(const OrdersRoute());
      },
      child: Container(
        height: 64.h,
        width: (MediaQuery.sizeOf(context).width - 42.w) / 2,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10.r),
          border: Border.all(color: AppStyle.primary),
        ),
        padding: EdgeInsets.symmetric(vertical: 8.h, horizontal: 16.w),
        child: Row(
          children: [
            Container(
              width: 36.r,
              height: 36.r,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: AppStyle.black,
              ),
              child: Icon(Remix.file_list_2_fill, color: AppStyle.primary),
            ),
            14.horizontalSpace,
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                4.verticalSpace,
                SizedBox(
                  width: 60.w,
                  child: Text(
                    AppHelpers.getTranslation(TrKeys.juvoBenefit),
                    style: AppStyle.interNormal(
                      size: 12.sp,
                      letterSpacing: -0.3,
                    ),
                    maxLines: 1,
                  ),
                ),
                Consumer(
                  builder: (context, ref, child) {
                    return Text(
                      AppHelpers.numberFormat(
                        number:
                            (ref
                                .watch(courierProfileStatisticsProvider)
                                .statistics
                                ?.data
                                ?.totalPrice ??
                            0),
                      ),
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        letterSpacing: -0.3,
                      ),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _balance(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // AppHelpers.showAlertDialog(
        //   context: context,
        //   child:  PushOrder(),
        // );
      },
      child: Container(
        height: 64.h,
        width: (MediaQuery.sizeOf(context).width - 42.w) / 2,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10.r),
          border: Border.all(color: AppStyle.white),
        ),
        padding: EdgeInsets.symmetric(vertical: 12.h, horizontal: 16.w),
        child: Row(
          children: [
            SvgPicture.asset(AppAssets.svgBalance),
            14.horizontalSpace,
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppHelpers.getTranslation(TrKeys.balance),
                  style: AppStyle.interNormal(size: 12.sp, letterSpacing: -0.3),
                ),
                Consumer(
                  builder: (context, ref, child) {
                    return Text(
                      AppHelpers.numberFormat(
                        number: LocalStorage.getUser()?.wallet?.price,
                      ),
                      style: AppStyle.interSemi(
                        size: 14.sp,
                        letterSpacing: -0.3,
                      ),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
