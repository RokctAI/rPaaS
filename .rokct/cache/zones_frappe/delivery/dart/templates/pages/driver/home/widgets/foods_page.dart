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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:delivery_sdk/src/driver/application/order/order_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';


import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/component/product_item.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class FoodsPage extends ConsumerStatefulWidget {
  final OrderDetailData order;

  const FoodsPage({super.key, required this.order});

  @override
  ConsumerState<FoodsPage> createState() => _FoodsPageState();
}

class _FoodsPageState extends ConsumerState<FoodsPage> {
  bool hasData = true;

  @override
  void initState() {
    if (widget.order.details?.isEmpty ?? true) {
      hasData = false;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(orderProvider.notifier)
            .showOrder(context, widget.order.id ?? '');
      });
    }
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(orderProvider);
    return state.isLoading
        ? const Loading()
        : SingleChildScrollView(
            padding: EdgeInsets.symmetric(horizontal: 16.w),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.foods)),
                16.verticalSpace,
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10.r),
                    color: AppStyle.white,
                  ),
                  padding: EdgeInsets.all(16.r),
                  child: Column(
                    children: [
                      ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: hasData
                              ? (widget.order.details?.length ?? 0)
                              : (state.order?.details?.length ?? 0),
                          itemBuilder: (context, index) {
                            return Padding(
                              padding: EdgeInsets.symmetric(vertical: 6.h),
                              child: Column(
                                children: [
                                  ProductItem(
                                    product: hasData
                                        ? (widget.order.details?[index].stock
                                            ?.product)
                                        : (state.order?.details?[index].stock
                                            ?.product),
                                    amount: hasData
                                        ? (widget
                                            .order.details?[index].quantity)
                                        : (state
                                            .order?.details?[index].quantity),
                                    price: AppHelpers.numberFormat(
                                        number: hasData
                                            ? (widget.order.details?[index]
                                                .totalPrice)
                                            : state.order?.details?[index]
                                                .totalPrice),
                                  ),
                                  if (state.order?.details?[index].note !=
                                          null &&
                                      state.order?.details?[index].note != '')
                                    Text(
                                      "${AppHelpers.getTranslation(TrKeys.note)}: ${state.order?.details?[index].note}",
                                      style: AppStyle.interRegular(
                                          color: AppStyle.blackColor,
                                          size: 14.sp,
                                          letterSpacing: -0.3),
                                    ),
                                ],
                              ),
                            );
                          }),
                      _priceItem(
                        title: TrKeys.subtotal,
                        price: hasData
                            ? widget.order.originPrice
                            : state.order?.originPrice,
                      ),
                      _priceItem(
                        title: TrKeys.tax,
                        price: hasData ? widget.order.tax : state.order?.tax,
                      ),
                      _priceItem(
                        title: TrKeys.serviceFee,
                        price: hasData
                            ? widget.order.serviceFee
                            : state.order?.serviceFee,
                      ),
                      _priceItem(
                        title: TrKeys.deliveryFee,
                        price: hasData
                            ? widget.order.deliveryFee
                            : state.order?.deliveryFee,
                      ),
                      _priceItem(
                        isDiscount: true,
                        title: TrKeys.discount,
                        price: hasData
                            ? widget.order.totalDiscount
                            : state.order?.totalDiscount,
                      ),
                      _priceItem(
                        isDiscount: true,
                        title: TrKeys.coupon,
                        price: state.order?.couponPrice,
                      ),
                      _priceItem(
                        isTotal: true,
                        title: TrKeys.total,
                        price: hasData
                            ? widget.order.totalPrice
                            : state.order?.totalPrice,
                      ),
                    ],
                  ),
                ),
                16.verticalSpace,
              ],
            ),
          );
  }

  _priceItem({
    required String title,
    required num? price,
    bool isTotal = false,
    bool isDiscount = false,
  }) {
    return (price ?? 0) == 0
        ? const SizedBox.shrink()
        : Column(
            children: [
              2.verticalSpace,
              Divider(color: AppStyle.black.withOpacity(0.4)),
              2.verticalSpace,
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    AppHelpers.getTranslation(title),
                    style: isTotal
                        ? AppStyle.interSemi(size: 16.sp, letterSpacing: -0.3)
                        : AppStyle.interNormal(
                            size: 14.sp,
                            letterSpacing: -0.3,
                            color: isDiscount ? AppStyle.red : AppStyle.black,
                          ),
                  ),
                  Text(
                    (isDiscount ? '-' : '') +
                        AppHelpers.numberFormat(number: price),
                    style: isTotal
                        ? AppStyle.interSemi(size: 16.sp, letterSpacing: -0.3)
                        : AppStyle.interNormal(
                            size: 14.sp,
                            letterSpacing: -0.3,
                            color: isDiscount ? AppStyle.red : AppStyle.black,
                          ),
                  )
                ],
              ),
            ],
          );
  }
}
