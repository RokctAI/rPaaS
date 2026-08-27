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
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';



import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/home/widgets/approve_dialog.dart';
import 'package:${package}/presentation/pages/home/widgets/foods_page.dart';
import 'package:${package}/presentation/pages/home/widgets/rate_customer.dart';
import 'package:${package}/presentation/component/order_item.dart';
import 'package:${package}/presentation/component/text_fields/underline_bordered_text_field.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_helpers.dart';

class DeliverBottomSheetScreen extends StatefulWidget {
  final OrderDetailData order;

  const DeliverBottomSheetScreen({super.key, required this.order});

  @override
  State<DeliverBottomSheetScreen> createState() =>
      _DeliverBottomSheetScreenState();
}

class _DeliverBottomSheetScreenState extends State<DeliverBottomSheetScreen> {
  TextEditingController noteCon = TextEditingController();
  TextEditingController amountCon = TextEditingController();

  final formKey = GlobalKey<FormState>();
  final cashFormKey = GlobalKey<FormState>();

  bool get _isCashOrder =>
      (widget.order.transaction?.paymentSystem?.tag ?? '').toLowerCase() ==
      'cash';

  /// 18+ order: the backend refuses to complete it until the courier
  /// confirms he checked the recipient's ID at the door.
  bool get _isAdultOrder => widget.order.containsAdultItems ?? false;

  @override
  void dispose() {
    noteCon.dispose();
    amountCon.dispose();
    super.dispose();
  }

  /// The delivered epilogue: finish the order, close the bottom sheet
  /// and ask for a customer rating. 18+ orders are intercepted first by
  /// a required ID-check confirmation dialog - every path that finishes
  /// a delivery (plain, cash collection, record-as-credit) funnels
  /// through here, so a flagged order can never complete unconfirmed.
  void _finishDelivery(BuildContext context, WidgetRef ref) {
    if (_isAdultOrder) {
      _showAgeVerificationDialog(context, ref);
      return;
    }
    _completeDelivery(context, ref, recipientAgeVerified: false);
  }

  void _completeDelivery(BuildContext context, WidgetRef ref,
      {required bool recipientAgeVerified}) {
    ref.read(homeProvider.notifier).deliveredFinish(
          context: context,
          orderId: widget.order.id,
          recipientAgeVerified: recipientAgeVerified,
        );
    Navigator.pop(context);
    AppHelpers.showCustomModalBottomSheet(
        context: context,
        modal: RateCustomer(
          order: widget.order,
        ),
        isDarkMode: false);
  }

  /// 18+ orders only (cash-collection dialog precedent): the courier
  /// must confirm he checked the recipient's ID (18 or older) before
  /// the order can be finished. Only this yes/no confirmation is
  /// recorded - no ID image or document data is ever captured or
  /// stored. Cancel leaves the order un-finished.
  void _showAgeVerificationDialog(BuildContext context, WidgetRef ref) {
    AppHelpers.showAlertDialog(
      context: context,
      child: StatefulBuilder(
        builder: (dialogContext, setState) {
          return Container(
            decoration: BoxDecoration(
              color: AppStyle.white,
              borderRadius: BorderRadius.circular(10.r),
            ),
            padding: EdgeInsets.symmetric(vertical: 30.h, horizontal: 24.w),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppHelpers.getTranslation(TrKeys.checkRecipientId18Plus),
                  textAlign: TextAlign.center,
                  style: AppStyle.interSemi(size: 16.sp),
                ),
                32.verticalSpace,
                Row(
                  children: [
                    Expanded(
                      child: CustomButton(
                        title: AppHelpers.getTranslation(TrKeys.cancel),
                        background: AppStyle.red,
                        textColor: AppStyle.white,
                        onPressed: () {
                          Navigator.pop(dialogContext);
                        },
                      ),
                    ),
                    10.horizontalSpace,
                    Expanded(
                      child: CustomButton(
                        title:
                            AppHelpers.getTranslation(TrKeys.confirmation),
                        background: AppStyle.black,
                        textColor: AppStyle.white,
                        onPressed: () {
                          Navigator.pop(dialogContext);
                          _completeDelivery(context, ref,
                              recipientAgeVerified: true);
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// Cash orders only: after the proof-of-delivery photo, confirm how much
  /// cash was actually received (server stays the authority on the expected
  /// amount) before the order is finished. When the driver's
  /// can_convert_cod_to_credit capability is enabled, a secondary action
  /// records the order as Credit (goods left, customer owes the shop)
  /// instead. A failed backend call keeps the dialog open and does NOT
  /// advance the status, so the order is never delivered-but-unrecorded.
  void _showCashCollectionDialog(
      BuildContext context, WidgetRef ref, bool canConvertToCredit) {
    amountCon.text = (widget.order.totalPrice ?? 0).toString();
    AppHelpers.showAlertDialog(
      context: context,
      child: StatefulBuilder(
        builder: (dialogContext, setState) {
          return Container(
            decoration: BoxDecoration(
              color: AppStyle.white,
              borderRadius: BorderRadius.circular(10.r),
            ),
            padding: EdgeInsets.symmetric(vertical: 30.h, horizontal: 24.w),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppHelpers.getTranslation(TrKeys.howMuchCashReceived),
                  textAlign: TextAlign.center,
                  style: AppStyle.interSemi(size: 16.sp),
                ),
                Form(
                  key: cashFormKey,
                  child: UnderlinedBorderTextField(
                    textController: amountCon,
                    label: AppHelpers.getTranslation(TrKeys.cashToCollect),
                    inputType:
                        const TextInputType.numberWithOptions(decimal: true),
                    validator: (value) {
                      final parsed = double.tryParse(value?.trim() ?? '');
                      if (parsed == null || parsed < 0) {
                        return AppHelpers.getTranslation(TrKeys.cannotBeEmpty);
                      }
                      return null;
                    },
                    onChanged: (value) {
                      setState(() {});
                    },
                  ),
                ),
                32.verticalSpace,
                CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.confirmation),
                  background: AppStyle.black,
                  textColor: AppStyle.white,
                  onPressed: () {
                    if (cashFormKey.currentState?.validate() ?? false) {
                      ref.read(homeProvider.notifier).confirmCodCollection(
                            context: context,
                            orderId: widget.order.id,
                            amountReceived:
                                double.parse(amountCon.text.trim()),
                            onSuccess: () {
                              Navigator.pop(dialogContext);
                              _finishDelivery(context, ref);
                            },
                          );
                    }
                  },
                ),
                if (canConvertToCredit) ...[
                  10.verticalSpace,
                  CustomButton(
                    title: AppHelpers.getTranslation(TrKeys.recordAsCredit),
                    background: AppStyle.transparent,
                    borderColor: AppStyle.black,
                    onPressed: () {
                      ref.read(homeProvider.notifier).convertCodToCredit(
                            context: context,
                            orderId: widget.order.id,
                            onSuccess: () {
                              Navigator.pop(dialogContext);
                              _finishDelivery(context, ref);
                            },
                          );
                    },
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.bottomCenter,
      child: Consumer(builder: (context, ref, child) {
        return SizedBox(
          height: ref.watch(homeProvider).isGoUser
              ? MediaQuery.sizeOf(context).height * 1.8 / 3
              : MediaQuery.sizeOf(context).height * 2 / 3,
          width: double.infinity,
          child: DraggableScrollableSheet(
              initialChildSize: 0.2,
              maxChildSize: 1,
              minChildSize: 0.16,
              snap: true,
              builder: (context, scrollController) => Container(
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
                              offset: const Offset(0, -2))
                        ]),
                    child: ListView(
                      controller: scrollController,
                      padding: EdgeInsets.only(
                          top: 8.h,
                          bottom: MediaQuery.paddingOf(context).bottom + 16.h,
                          left: 16.w,
                          right: 16.w),
                      children: [
                        Container(
                          height: 4.h,
                          margin: EdgeInsets.symmetric(
                              horizontal:
                                  (MediaQuery.sizeOf(context).width - 100.w) /
                                      2),
                          decoration: BoxDecoration(
                            color: AppStyle.dragElement,
                            borderRadius: BorderRadius.circular(40.r),
                          ),
                        ),
                        24.verticalSpace,
                        OrderItem(
                          order: widget.order,
                          isDeliveryShop:
                              ref.watch(homeProvider).isGoRestaurant,
                          isDeliveryClient: ref.watch(homeProvider).isGoUser,
                        ),
                        24.verticalSpace,
                        if (_isCashOrder) ...[
                          Container(
                            width: double.infinity,
                            padding: EdgeInsets.all(16.r),
                            decoration: BoxDecoration(
                              color: AppStyle.white,
                              borderRadius: BorderRadius.circular(10.r),
                              border: Border.all(color: AppStyle.primary),
                            ),
                            child: Text(
                              "${AppHelpers.getTranslation(TrKeys.cashToCollect)}: ${AppHelpers.numberFormat(number: widget.order.totalPrice ?? 0)}",
                              textAlign: TextAlign.center,
                              style: AppStyle.interBold(
                                size: 16.sp,
                                color: AppStyle.primary,
                              ),
                            ),
                          ),
                          16.verticalSpace,
                        ],
                        ref.watch(homeProvider).isGoRestaurant
                            ? Column(
                                children: [
                                  CustomButton(
                                    title: AppHelpers.getTranslation(
                                        TrKeys.orderInformation),
                                    onPressed: () {
                                      AppHelpers.showCustomModalBottomSheet(
                                          context: context,
                                          modal: FoodsPage(
                                            order: widget.order,
                                          ),
                                          isDarkMode: false);
                                    },
                                    background: AppStyle.transparent,
                                    borderColor: AppStyle.black,
                                  ),
                                  10.verticalSpace,
                                ],
                              )
                            : const SizedBox.shrink(),
                        CustomButton(
                          title: ref.watch(homeProvider).isGoRestaurant
                              ? AppHelpers.getTranslation(
                                  TrKeys.completeCheckout)
                              : AppHelpers.getTranslation(
                                  TrKeys.iDeliveredTheOrder),
                          onPressed: () {
                            if (ref.watch(homeProvider).isGoRestaurant) {
                              AppHelpers.showAlertDialog(
                                  context: context,
                                  child: ApproveOrderDialog(
                                    order: widget.order,
                                  ));
                            } else {
                              CourierHelpers.openDialogImagePicker(
                                context: context,
                                onSuccess: (path) async {
                                  if (context.mounted) {
                                    if (path.isNotEmpty) {
                                      ref
                                          .read(homeProvider.notifier)
                                          .uploadImage(
                                            context: context,
                                            orderId: widget.order.id,
                                            path: path,
                                          );
                                    }
                                    if (_isCashOrder) {
                                      // Cash orders confirm the received
                                      // amount (or record credit) BEFORE
                                      // the order is finished.
                                      final canConvertToCredit = await ref
                                          .read(homeProvider.notifier)
                                          .fetchCanConvertCodToCredit();
                                      if (!context.mounted) return;
                                      _showCashCollectionDialog(
                                          context, ref, canConvertToCredit);
                                    } else {
                                      _finishDelivery(context, ref);
                                    }
                                  }
                                },
                              );
                            }
                          },
                        ),
                        const SizedBox(
                          height: 10,
                        ),
                        CustomButton(
                          title: AppHelpers.getTranslation(TrKeys.cancel),
                          textColor: Colors.white,
                          background: AppStyle.red,
                          onPressed: () {
                            AppHelpers.showAlertDialog(
                              context: context,
                              child: StatefulBuilder(
                                builder: (context, setState) {
                                  return Container(
                                    decoration: BoxDecoration(
                                      color: AppStyle.white,
                                      borderRadius: BorderRadius.circular(10.r),
                                    ),
                                    padding: EdgeInsets.symmetric(
                                        vertical: 30.h, horizontal: 24.w),
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        RichText(
                                          textAlign: TextAlign.center,
                                          text: TextSpan(
                                            text: AppHelpers.getTranslation(
                                                TrKeys.areYouSure),
                                            style:
                                                AppStyle.interNormal(size: 16.sp),
                                          ),
                                        ),
                                        Form(
                                          key: formKey,
                                          child: UnderlinedBorderTextField(
                                            textController: noteCon,
                                            label: 'Note',
                                            validator: (p0) {
                                              if (p0?.isEmpty ?? true) {
                                                return AppHelpers
                                                    .getTranslation(
                                                        TrKeys.cannotBeEmpty);
                                              }
                                              return null;
                                            },
                                            onChanged: (value) {
                                              setState(() {});
                                            },
                                          ),
                                        ),
                                        32.verticalSpace,
                                        Row(
                                          children: [
                                            Expanded(
                                              child: CustomButton(
                                                title:
                                                    AppHelpers.getTranslation(
                                                        TrKeys.cancel),
                                                background: AppStyle.red,
                                                textColor: AppStyle.white,
                                                onPressed: () {
                                                  Navigator.pop(context);
                                                },
                                              ),
                                            ),
                                            10.horizontalSpace,
                                            Expanded(
                                              child: Consumer(
                                                builder: (context, ref, child) {
                                                  return CustomButton(
                                                    title: AppHelpers
                                                        .getTranslation(TrKeys
                                                            .confirmation),
                                                    background: AppStyle.black,
                                                    textColor: AppStyle.white,
                                                    borderColor:
                                                        Colors.transparent,
                                                    onPressed: () {
                                                      if ((formKey.currentState
                                                                  ?.validate() ??
                                                              false) &&
                                                          widget.order.id !=
                                                              null) {
                                                        ref
                                                            .read(homeProvider
                                                                .notifier)
                                                            .cancelOrder(
                                                                context:
                                                                    context,
                                                                orderId: widget
                                                                    .order.id!,
                                                                note: noteCon
                                                                    .text);
                                                        Navigator.pop(context);
                                                      }

                                                      /// TODO CANCEL ORDER AND SEND NOTE
                                                    },
                                                  );
                                                },
                                              ),
                                            )
                                          ],
                                        )
                                      ],
                                    ),
                                  );
                                },
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                  )),
        );
      }),
    );
  }
}
