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
import 'package:auto_route/auto_route.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'widgets/payment_item.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/create_order/order/widgets/title_price.dart';
import 'package:${package}/presentation/component/select_date_modal.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/create_order_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/address/order/order_address_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/delivery/delivery_type_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/payment/order_payment_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/section/section_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/table/table_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/time/delivery_time_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/user/order_user_provider.dart';
import 'package:orders_sdk/src/manager/application/order_cart/order_cart_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/appbar/home_appbar_provider.dart';
import 'package:orders_sdk/src/manager/application/orders/new/new_orders_provider.dart';


@RoutePage(name: 'ManagerDeliveryTimeRoute')
class DeliveryTimePage extends ConsumerStatefulWidget {
  const DeliveryTimePage({super.key});

  @override
  ConsumerState<DeliveryTimePage> createState() => _DeliveryTimePageState();
}

class _DeliveryTimePageState extends ConsumerState<DeliveryTimePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        ref.read(orderPaymentProvider.notifier)
          ..fetchPayments(ref.watch(deliveryTypeProvider).type)
          ..getCalculate(
            stocks: ref.watch(orderCartProvider).stocks,
            type: ref.watch(deliveryTypeProvider).type,
            location: ref.watch(orderAddressProvider).location,
          );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Scaffold(
        resizeToAvoidBottomInset: false,
        backgroundColor: AppStyle.bgGrey,
        body: Container(
          padding: MediaQuery.viewInsetsOf(context),
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              bottom: MediaQuery.paddingOf(context).bottom + 48.h,
            ),
            child: Column(
              children: [
                Consumer(
                  builder: (context, ref, child) {
                    return Container(
                      decoration: BoxDecoration(
                        color: AppStyle.white,
                        borderRadius: BorderRadius.only(
                          bottomLeft: Radius.circular(10.r),
                          bottomRight: Radius.circular(10.r),
                        ),
                      ),
                      padding: REdgeInsets.only(
                        top: MediaQuery.paddingOf(context).top + 26,
                        left: 16,
                        right: 16,
                        bottom: 16,
                      ),
                      child: Consumer(
                        builder: (context, ref, child) {
                          final timeState = ref.watch(deliveryTimeProvider);
                          final timeEvent =
                              ref.read(deliveryTimeProvider.notifier);
                          return Column(
                            children: [
                              TitleAndIcon(
                                title: AppHelpers.getTranslation(
                                    TrKeys.deliveryTime),
                              ),
                              24.verticalSpace,
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    AppHelpers.getTranslation(
                                        TrKeys.selectedTimeAndDay),
                                    style: AppStyle.interSemi(
                                        size: 14.sp, letterSpacing: -0.3),
                                  ),
                                  GestureDetector(
                                    onTap: () =>
                                        AppHelpers.showCustomModalBottomSheet(
                                      paddingTop:
                                          MediaQuery.paddingOf(context).top,
                                      context: context,
                                      radius: 12,
                                      modal: SelectDateModal(
                                        initialDate: timeState.deliveryDate,
                                        onDateSaved: (date) =>
                                            timeEvent.setDeliveryDate(
                                          date.toString().substring(0, 10),
                                        ),
                                      ),
                                      isDarkMode: true,
                                    ),
                                    child: Text(
                                      timeState.deliveryDate,
                                      style: AppStyle.interNormal(
                                          size: 14.sp, letterSpacing: -0.3),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          );
                        },
                      ),
                    );
                  },
                ),
                Consumer(
                  builder: (context, ref, child) {
                    return Container(
                      margin: EdgeInsets.symmetric(vertical: 10.h),
                      decoration: BoxDecoration(
                        color: AppStyle.white,
                        borderRadius: BorderRadius.circular(10.r),
                      ),
                      padding: REdgeInsets.symmetric(
                        vertical: 24,
                        horizontal: 16,
                      ),
                      child: Column(
                        children: [
                          TitleAndIcon(
                            title: AppHelpers.getTranslation(TrKeys.payment),
                          ),
                          Consumer(
                            builder: (context, ref, child) {
                              final paymentState =
                                  ref.watch(orderPaymentProvider);
                              final paymentEvent =
                                  ref.watch(orderPaymentProvider.notifier);
                              return paymentState.isLoading
                                  ? Container(
                                      width: 30.r,
                                      height: 30.r,
                                      margin:
                                          REdgeInsets.symmetric(vertical: 20),
                                      child: Center(
                                        child: CircularProgressIndicator(
                                          strokeWidth: 3.r,
                                          color: AppStyle.primary,
                                        ),
                                      ),
                                    )
                                  : ListView.builder(
                                      itemCount: paymentState.payments.length,
                                      shrinkWrap: true,
                                      padding:
                                          REdgeInsets.symmetric(vertical: 18),
                                      physics:
                                          const NeverScrollableScrollPhysics(),
                                      itemBuilder: (context, index) =>
                                          PaymentItem(
                                        payment: paymentState.payments[index],
                                        isSelected:
                                            paymentState.selectedIndex == index,
                                        isLast: paymentState.payments.length ==
                                            index + 1,
                                        onTap: () => paymentEvent
                                            .setSelectedIndex(index),
                                      ),
                                    );
                            },
                          ),
                        ],
                      ),
                    );
                  },
                ),
                Consumer(builder: (context, ref, child) {
                  final state = ref.watch(orderPaymentProvider);
                  return Container(
                    margin: EdgeInsets.symmetric(vertical: 10.h),
                    decoration: BoxDecoration(
                      color: AppStyle.white,
                      borderRadius: BorderRadius.circular(10.r),
                    ),
                    padding: EdgeInsets.symmetric(vertical: 24.h),
                    child: state.isCalculateLoading
                        ? const Loading()
                        : Column(
                            children: [
                              Padding(
                                padding: EdgeInsets.symmetric(horizontal: 16.w),
                                child: TitleAndIcon(
                                  title:
                                      "${AppHelpers.getTranslation(TrKeys.payment)} - \$",
                                ),
                              ),
                              24.verticalSpace,
                              TitleAndPrice(
                                title:
                                    AppHelpers.getTranslation(TrKeys.subtotal),
                                rightTitle: AppHelpers.numberFormat(number: state.orderCalculate?.price ?? 0),
                                textStyle: AppStyle.interRegular(
                                  size: 16,
                                  letterSpacing: -0.3,
                                ),
                              ),
                              16.verticalSpace,
                              TitleAndPrice(
                                title: AppHelpers.getTranslation(
                                    TrKeys.deliveryPrice),
                                rightTitle: AppHelpers.numberFormat(number: state.orderCalculate?.deliveryFee ?? 0),
                                textStyle: AppStyle.interRegular(
                                    size: 16, letterSpacing: -0.3),
                              ),
                              16.verticalSpace,
                              TitleAndPrice(
                                title: AppHelpers.getTranslation(
                                    TrKeys.serviceFee),
                                rightTitle: AppHelpers.numberFormat(number: state.orderCalculate?.serviceFee ?? 0),
                                textStyle: AppStyle.interRegular(
                                    size: 16, letterSpacing: -0.3),
                              ),
                              16.verticalSpace,
                              TitleAndPrice(
                                title:
                                    AppHelpers.getTranslation(TrKeys.discount),
                                rightTitle:
                                    '-${AppHelpers.numberFormat(number: state.orderCalculate?.totalDiscount ?? 0)}',
                                textStyle: AppStyle.interRegular(
                                    size: 16, letterSpacing: -0.3),
                              ),
                              16.verticalSpace,
                              TitleAndPrice(
                                title:
                                    AppHelpers.getTranslation(TrKeys.totalTax),
                                rightTitle: AppHelpers.numberFormat(number: state.orderCalculate?.totalShopTax ?? 0),
                                textStyle: AppStyle.interRegular(
                                    size: 16, letterSpacing: -0.3),
                              ),
                              16.verticalSpace,
                              Divider(color: AppStyle.shimmerBase),
                              16.verticalSpace,
                              TitleAndPrice(
                                title: AppHelpers.getTranslation(TrKeys.total),
                                rightTitle: AppHelpers.numberFormat(number: state.orderCalculate?.totalPrice ?? 0),
                                textStyle: AppStyle.interSemi(
                                    size: 20, letterSpacing: -0.3),
                              ),
                            ],
                          ),
                  );
                }),
              ],
            ),
          ),
        ),
        floatingActionButtonLocation:
            FloatingActionButtonLocation.miniCenterDocked,
        floatingActionButton: Padding(
          padding: REdgeInsets.all(16),
          child: Row(
            children: [
              const PopButton(heroTag: AppConstants.heroTagAddOrderButton),
              8.horizontalSpace,
              Expanded(
                child: Consumer(
                  builder: (context, ref, child) {
                    final addressState = ref.watch(orderAddressProvider);
                    final paymentState = ref.watch(orderPaymentProvider);
                    final userState = ref.watch(orderUserProvider);
                    return CustomButton(
                      title: AppHelpers.getTranslation(TrKeys.next),
                      isLoading: ref.watch(createOrderProvider).isCreating,
                      onPressed: () {
                        if (paymentState.payments[paymentState.selectedIndex]
                                .payment?.tag ==
                            'wallet') {
                          final num walletPrice =
                              userState.selectedUser?.wallet?.price ?? 0;
                          final num orderPrice =
                              paymentState.orderCalculate?.totalPrice ?? 0;
                          if (walletPrice < orderPrice) {
                            AppHelpers.showCheckTopSnackBar(
                              context,
                              AppHelpers.getTranslation(
                                  TrKeys.notEnoughMoney),
                            );
                            return;
                          }
                        }
                        ref.read(createOrderProvider.notifier).createOrder(
                              deliveryType:
                                  ref.watch(deliveryTypeProvider).type,
                              user: userState.selectedUser,
                              stocks: ref
                                      .watch(orderPaymentProvider)
                                      .orderCalculate
                                      ?.stocks ??
                                  ref.watch(orderCartProvider).stocks,
                              deliveryDate:
                                  ref.watch(deliveryTimeProvider).deliveryDate,
                              address: addressState.textController?.text ?? '',
                              location: addressState.location,
                              entrance: addressState.entrance,
                              floor: addressState.floor,
                              house: addressState.house,
                              paymentId: paymentState
                                  .payments[paymentState.selectedIndex]
                                  .payment
                                  ?.id,
                              orderSuccess: (String orderId) {
                                context.router.popUntilRoot();
                                ref.read(orderCartProvider.notifier).clearAll();
                                ref
                                    .read(orderUserProvider.notifier)
                                    .clearSelectedUserInfo();
                                ref
                                    .read(tableProvider.notifier)
                                    .clearSelectTableInfo();
                                ref
                                    .read(sectionProvider.notifier)
                                    .clearSelectSectionInfo();
                                ref
                                    .read(newOrdersProvider.notifier)
                                    .fetchNewOrders(
                                      context: context,
                                      isRefresh: true,
                                      activeTabIndex:
                                          ref.watch(homeAppbarProvider).index,
                                    );
                                ref
                                    .read(orderPaymentProvider.notifier)
                                    .createTransaction(
                                        context,
                                        orderId,
                                        paymentState
                                            .payments[
                                                paymentState.selectedIndex]
                                            .payment
                                            ?.id);
                              },
                              // Sale queued locally (backend unreachable):
                              // same cleanup, but no createTransaction — the
                              // queued op carries payment_id and the sync
                              // handler creates the transaction after the
                              // order lands.
                              orderQueued: (String localId) {
                                context.router.popUntilRoot();
                                ref.read(orderCartProvider.notifier).clearAll();
                                ref
                                    .read(orderUserProvider.notifier)
                                    .clearSelectedUserInfo();
                                ref
                                    .read(tableProvider.notifier)
                                    .clearSelectTableInfo();
                                ref
                                    .read(sectionProvider.notifier)
                                    .clearSelectSectionInfo();
                                ref
                                    .read(newOrdersProvider.notifier)
                                    .fetchNewOrders(
                                      context: context,
                                      isRefresh: true,
                                      activeTabIndex:
                                          ref.watch(homeAppbarProvider).index,
                                    );
                              },
                              failed: (message) =>
                                  AppHelpers.showCheckTopSnackBar(
                                context,
                                message,
                              ),
                              tableId: ref.watch(tableProvider).selectTable?.id,
                            );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
