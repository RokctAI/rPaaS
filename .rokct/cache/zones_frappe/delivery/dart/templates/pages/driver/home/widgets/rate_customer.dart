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
import 'package:flutter_rating_bar/flutter_rating_bar.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:base_sdk/src/models/data/parcel_order.dart';

import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/home/widgets/add_comment.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';

class RateCustomer extends StatefulWidget {
  final OrderDetailData? order;
  final ParcelOrder? parcel;

  const RateCustomer({super.key, this.order, this.parcel});

  @override
  State<RateCustomer> createState() => _RateCustomerState();
}

class _RateCustomerState extends State<RateCustomer> {
  double rate = 0;
  String note = "";

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 16.w),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.evaluation)),
          Text(
            AppHelpers.getTranslation(TrKeys.yourFeedbackService),
            style: AppStyle.interNormal(size: 14.sp),
          ),
          24.verticalSpace,
          Text(
            AppHelpers.getTranslation(TrKeys.rateTheCustomer),
            style: AppStyle.interSemi(size: 16.sp),
          ),
          14.verticalSpace,
          Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppStyle.white,
              borderRadius: BorderRadius.circular(10.r),
            ),
            padding: EdgeInsets.all(16.r),
            child: RatingBar.builder(
              itemBuilder: (context, index) =>
                  Icon(Remix.star_fill, color: AppStyle.primary),
              itemCount: 5,
              itemPadding: EdgeInsets.symmetric(horizontal: 11.r),
              direction: Axis.horizontal,
              onRatingUpdate: (double value) {
                rate = value;
              },
              glow: false,
            ),
          ),
          14.verticalSpace,
          _addComment(context),
          24.verticalSpace,
          Consumer(
            builder: (context, ref, child) {
              return CustomButton(
                title: AppHelpers.getTranslation(TrKeys.send),
                onPressed: () {
                  Navigator.pop(context);
                  if (widget.order == null) {
                    ref
                        .read(homeProvider.notifier)
                        .addReviewParcel(
                          context: context,
                          parcelId: widget.parcel?.id,
                          rating: rate,
                          comment: note,
                        );
                  } else {
                    ref
                        .read(homeProvider.notifier)
                        .addReview(
                          context: context,
                          orderId: widget.order?.id,
                          rating: rate,
                          comment: note,
                        );
                  }
                },
              );
            },
          ),
          16.verticalSpace,
        ],
      ),
    );
  }

  Widget _addComment(BuildContext context) {
    return GestureDetector(
      onTap: () {
        AppHelpers.showCustomModalBottomSheet(
          context: context,
          modal: AddComment(
            onChange: (s) {
              note = s;
            },
          ),
          isDarkMode: false,
        );
      },
      child: Container(
        decoration: BoxDecoration(
          color: AppStyle.white,
          borderRadius: BorderRadius.circular(10.r),
        ),
        padding: EdgeInsets.symmetric(vertical: 12.h, horizontal: 16.w),
        child: Row(
          children: [
            const Icon(Remix.chat_1_fill),
            12.horizontalSpace,
            Text(
              note.isEmpty
                  ? AppHelpers.getTranslation(TrKeys.noteAboutClient)
                  : note,
              style: AppStyle.interRegular(size: 13.sp, color: AppStyle.black),
            ),
          ],
        ),
      ),
    );
  }
}
