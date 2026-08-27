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
import 'package:map_launcher/map_launcher.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:base_sdk/src/models/data/parcel_order.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:${package}/presentation/component/maps_list.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:intl/intl.dart' as intl;

import 'package:${package}/presentation/pages/home/widgets/approve_dialog.dart';
import 'package:${package}/presentation/pages/home/widgets/rate_customer.dart';

class ParcelBottomSheetScreen extends StatelessWidget {
  final ParcelOrder? parcel;

  const ParcelBottomSheetScreen({super.key, required this.parcel});

  /// Sender-declared cash the driver must collect from the recipient
  /// (off-platform sale). Arrives via base_sdk's ParcelOrder.codAmount.
  bool get _hasCodToCollect => (parcel?.codAmount ?? 0) > 0;

  /// The original delivered epilogue: finish the parcel and ask for a
  /// customer rating.
  void _finishParcelDelivery(BuildContext context, WidgetRef ref) {
    ref.read(homeProvider.notifier).deliveredFinishParcel(
          context: context,
          parcelId: parcel?.id,
        );
    AppHelpers.showCustomModalBottomSheet(
      context: context,
      modal: RateCustomer(parcel: parcel),
      isDarkMode: false,
    );
  }

  /// COD parcels only: confirm the cash actually received from the
  /// recipient before finishing. On backend acceptance the amount is
  /// settled from the deliveryman's wallet to the sender's wallet. A
  /// failed call keeps the dialog open and does NOT advance the status.
  void _showParcelCashCollectionDialog(BuildContext context, WidgetRef ref) {
    final amountCon = TextEditingController(
      text: (parcel?.codAmount ?? 0).toString(),
    );
    final cashFormKey = GlobalKey<FormState>();
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
                16.verticalSpace,
                Form(
                  key: cashFormKey,
                  child: TextFormField(
                    controller: amountCon,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: AppHelpers.getTranslation(
                          TrKeys.collectFromRecipient),
                    ),
                    validator: (value) {
                      final parsed = double.tryParse(value?.trim() ?? '');
                      if (parsed == null || parsed < 0) {
                        return AppHelpers.getTranslation(TrKeys.cannotBeEmpty);
                      }
                      return null;
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
                      ref
                          .read(homeProvider.notifier)
                          .confirmParcelCodCollection(
                            context: context,
                            parcelId: parcel?.id,
                            amountReceived:
                                double.parse(amountCon.text.trim()),
                            onSuccess: () {
                              Navigator.pop(dialogContext);
                              _finishParcelDelivery(context, ref);
                            },
                          );
                    }
                  },
                ),
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
      child: Consumer(
        builder: (context, ref, child) {
          return SizedBox(
            height: ref.watch(homeProvider).isGoUser
                ? MediaQuery.sizeOf(context).height * 1.8 / 3
                : MediaQuery.sizeOf(context).height * 2 / 3,
            width: double.infinity,
            child: DraggableScrollableSheet(
              initialChildSize: 0.2,
              maxChildSize: 0.65,
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
                      offset: const Offset(0, -2),
                    ),
                  ],
                ),
                child: ListView(
                  controller: scrollController,
                  padding: EdgeInsets.only(
                    top: 8.h,
                    bottom: MediaQuery.paddingOf(context).bottom + 16.h,
                    left: 16.w,
                    right: 16.w,
                  ),
                  children: [
                    Container(
                      height: 4.h,
                      margin: EdgeInsets.symmetric(
                        horizontal:
                            (MediaQuery.sizeOf(context).width - 100.w) / 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppStyle.dragElement,
                        borderRadius: BorderRadius.circular(40.r),
                      ),
                    ),
                    24.verticalSpace,
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            16.horizontalSpace,
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  width:
                                      MediaQuery.sizeOf(context).width - 180.w,
                                  child: Text(
                                    parcel?.addressFrom?.address ?? "",
                                    style: AppStyle.interSemi(
                                      size: 14.sp,
                                      letterSpacing: -0.3,
                                    ),
                                  ),
                                ),
                                2.verticalSpace,
                                IntrinsicHeight(
                                  child: Row(
                                    children: [
                                      Text(
                                        "№ ${parcel?.id}",
                                        style: AppStyle.interNormal(
                                          size: 14.sp,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                      const VerticalDivider(),
                                      Text(
                                        intl.DateFormat("hh:mm").format(
                                          parcel?.updatedAt ?? DateTime.now(),
                                        ),
                                        style: AppStyle.interNormal(
                                          size: 14.sp,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                      16.horizontalSpace,
                                      Icon(Remix.building_fill, size: 18.r),
                                      IconButton(
                                        padding: EdgeInsets.symmetric(
                                          horizontal: 6.w,
                                        ),
                                        onPressed: () async {
                                          AppHelpers.showCustomModalBottomSheet(
                                            context: context,
                                            modal: MapsList(
                                              location: Coords(
                                                parcel?.addressFrom?.latitude ??
                                                    0,
                                                parcel
                                                        ?.addressFrom
                                                        ?.longitude ??
                                                    0,
                                              ),
                                              title: "A",
                                            ),
                                            isDarkMode: false,
                                          );
                                        },
                                        icon: Icon(
                                          Remix.map_2_fill,
                                          size: 18.r,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const Spacer(),
                            Row(
                              children: [
                                GestureDetector(
                                  onTap: () async {
                                    final Uri launchUri = Uri(
                                      scheme: 'tel',
                                      path: parcel?.phoneFrom ?? "",
                                    );
                                    await launchUrl(launchUri);
                                  },
                                  child: Container(
                                    height: 38.r,
                                    width: 38.r,
                                    decoration: const BoxDecoration(
                                      color: AppStyle.black,
                                      shape: BoxShape.circle,
                                    ),
                                    margin: EdgeInsets.all(4.r),
                                    child: Icon(
                                      Remix.phone_fill,
                                      color: AppStyle.white,
                                      size: 20.r,
                                    ),
                                  ),
                                ),
                                GestureDetector(
                                  onTap: () async {
                                    final Uri launchUri = Uri(
                                      scheme: 'sms',
                                      path: parcel?.phoneFrom ?? "",
                                    );
                                    await launchUrl(launchUri);
                                  },
                                  child: Container(
                                    height: 38.r,
                                    width: 38.r,
                                    decoration: const BoxDecoration(
                                      color: AppStyle.black,
                                      shape: BoxShape.circle,
                                    ),
                                    margin: EdgeInsets.all(4.r),
                                    child: Icon(
                                      Remix.chat_1_fill,
                                      color: AppStyle.white,
                                      size: 20.r,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                        24.verticalSpace,
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            16.horizontalSpace,
                            SizedBox(
                              width: MediaQuery.sizeOf(context).width - 180.w,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(
                                    width:
                                        MediaQuery.sizeOf(context).width -
                                        190.w,
                                    child: Text(
                                      parcel?.addressTo?.address ?? "",
                                      style: AppStyle.interSemi(
                                        size: 14.sp,
                                        letterSpacing: -0.3,
                                      ),
                                      maxLines: 1,
                                    ),
                                  ),
                                  2.verticalSpace,
                                  IntrinsicHeight(
                                    child: Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            parcel?.usernameTo ?? "",
                                            style: AppStyle.interNormal(
                                              size: 12.sp,
                                              letterSpacing: -0.3,
                                            ),
                                          ),
                                        ),
                                        const VerticalDivider(),
                                        Text(
                                          parcel?.phoneTo ?? "",
                                          style: AppStyle.interNormal(
                                            size: 12.sp,
                                            letterSpacing: -0.3,
                                          ),
                                        ),
                                        IconButton(
                                          padding: EdgeInsets.symmetric(
                                            horizontal: 6.w,
                                          ),
                                          onPressed: () {
                                            AppHelpers.showCustomModalBottomSheet(
                                              context: context,
                                              modal: MapsList(
                                                location: Coords(
                                                  parcel?.addressTo?.latitude ??
                                                      0,
                                                  parcel
                                                          ?.addressTo
                                                          ?.longitude ??
                                                      0,
                                                ),
                                                title: "B",
                                              ),
                                              isDarkMode: false,
                                            );
                                          },
                                          icon: Icon(
                                            Remix.map_2_fill,
                                            size: 18.r,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Spacer(),
                            Row(
                              children: [
                                GestureDetector(
                                  onTap: () async {
                                    final Uri launchUri = Uri(
                                      scheme: 'tel',
                                      path: parcel?.phoneTo ?? "",
                                    );
                                    await launchUrl(launchUri);
                                  },
                                  child: Container(
                                    height: 38.r,
                                    width: 38.r,
                                    decoration: const BoxDecoration(
                                      color: AppStyle.black,
                                      shape: BoxShape.circle,
                                    ),
                                    margin: EdgeInsets.all(4.r),
                                    child: Icon(
                                      Remix.phone_fill,
                                      color: AppStyle.white,
                                      size: 20.r,
                                    ),
                                  ),
                                ),
                                GestureDetector(
                                  onTap: () async {
                                    final Uri launchUri = Uri(
                                      scheme: 'sms',
                                      path: parcel?.phoneTo ?? "",
                                    );
                                    await launchUrl(launchUri);
                                  },
                                  child: Container(
                                    height: 38.r,
                                    width: 38.r,
                                    decoration: const BoxDecoration(
                                      color: AppStyle.black,
                                      shape: BoxShape.circle,
                                    ),
                                    margin: EdgeInsets.all(4.r),
                                    child: Icon(
                                      Remix.chat_1_fill,
                                      color: AppStyle.white,
                                      size: 20.r,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                    24.verticalSpace,
                    if (_hasCodToCollect) ...[
                      Container(
                        width: double.infinity,
                        padding: EdgeInsets.all(16.r),
                        decoration: BoxDecoration(
                          color: AppStyle.white,
                          borderRadius: BorderRadius.circular(10.r),
                          border: Border.all(color: AppStyle.primary),
                        ),
                        child: Text(
                          "${AppHelpers.getTranslation(TrKeys.collectFromRecipient)}: ${AppHelpers.numberFormat(number: parcel?.codAmount ?? 0)}",
                          textAlign: TextAlign.center,
                          style: AppStyle.interBold(
                            size: 16.sp,
                            color: AppStyle.primary,
                          ),
                        ),
                      ),
                      16.verticalSpace,
                    ],
                    CustomButton(
                      title: ref.watch(homeProvider).isGoRestaurant
                          ? AppHelpers.getTranslation(TrKeys.completeCheckout)
                          : AppHelpers.getTranslation(
                              TrKeys.iDeliveredTheOrder,
                            ),
                      onPressed: () {
                        if (ref.watch(homeProvider).isGoRestaurant) {
                          AppHelpers.showAlertDialog(
                            context: context,
                            child: ApproveOrderDialog(parcel: parcel),
                          );
                        } else if (_hasCodToCollect) {
                          // COD parcels confirm the collected cash before
                          // the parcel is finished.
                          _showParcelCashCollectionDialog(context, ref);
                        } else {
                          _finishParcelDelivery(context, ref);
                        }
                      },
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
