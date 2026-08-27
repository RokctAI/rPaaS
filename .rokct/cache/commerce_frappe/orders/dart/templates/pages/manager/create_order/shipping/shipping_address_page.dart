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
import 'package:flutter/services.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:intl_phone_field/intl_phone_field.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'widgets/delivery_type_item.dart';
import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/presentation/components/text_fields/underlined_text_field.dart';
import 'package:${package}/presentation/pages/main/widgets/buttons_bouncing_effect.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/address/order/order_address_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/delivery/delivery_type_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/section/section_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/table/table_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/user/order_user_provider.dart';

@RoutePage(name: 'ManagerShippingAddressRoute')
class ShippingAddressPage extends StatefulWidget {
  const ShippingAddressPage({super.key});

  @override
  State<ShippingAddressPage> createState() => _ShippingAddressPageState();
}

class _ShippingAddressPageState extends State<ShippingAddressPage> {
  late TextEditingController _userTextController;

  @override
  void initState() {
    super.initState();
    _userTextController = TextEditingController();
  }

  @override
  void dispose() {
    super.dispose();
    _userTextController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Scaffold(
        resizeToAvoidBottomInset: false,
        backgroundColor: AppStyle.bgGrey,
        body: Consumer(
          builder: (context, ref, child) {
            final deliveryEvent = ref.read(deliveryTypeProvider.notifier);
            final deliveryState = ref.watch(deliveryTypeProvider);
            return Container(
              padding: MediaQuery.viewInsetsOf(context),
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Column(
                  children: [
                    Container(
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
                          24.verticalSpace,
                          TitleAndIcon(
                            title: AppHelpers.getTranslation(
                              TrKeys.deliveryType,
                            ),
                          ),
                          24.verticalSpace,
                          DeliveryTypeItem(
                            iconData: Remix.takeaway_fill,
                            title: AppHelpers.getTranslation(
                              TrKeys.deliveryService,
                            ),
                            desc:
                                '${AppHelpers.getTranslation(TrKeys.estimatedTime)} 25 - 30 min',
                            isActive: deliveryState.type == TrKeys.delivery,
                            onTap: () => deliveryEvent.setType(TrKeys.delivery),
                          ),
                          8.verticalSpace,
                          DeliveryTypeItem(
                            iconData: Remix.walk_fill,
                            title: AppHelpers.getTranslation(TrKeys.takeAway),
                            desc:
                                '${AppHelpers.getTranslation(TrKeys.approximateTime)} 25 - 30 min',
                            isActive: deliveryState.type == TrKeys.pickup,
                            onTap: () => deliveryEvent.setType(TrKeys.pickup),
                          ),
                          8.verticalSpace,
                          DeliveryTypeItem(
                            iconData: Icons.table_restaurant,
                            title: AppHelpers.getTranslation(TrKeys.dineIn),
                            desc:
                                '${AppHelpers.getTranslation(TrKeys.approximateTime)} 25 - 30 min',
                            isActive: deliveryState.type == TrKeys.dineIn,
                            onTap: () => deliveryEvent.setType(TrKeys.dineIn),
                          ),
                        ],
                      ),
                    ),
                    10.verticalSpace,
                    if (deliveryState.type == TrKeys.delivery)
                      Container(
                        margin: REdgeInsets.only(bottom: 12),
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
                              title: AppHelpers.getTranslation(
                                TrKeys.customerInformation,
                              ),
                            ),
                            24.verticalSpace,
                            Consumer(
                              builder: (context, ref, child) {
                                final userState = ref.watch(orderUserProvider);
                                final userNotifier = ref.read(
                                  orderUserProvider.notifier,
                                );
                                ref.listen(orderUserProvider, (p, n) {
                                  if (p?.selectedUser != n.selectedUser) {
                                    _userTextController.text =
                                        n.selectedUser?.phone ?? '';
                                  }
                                });

                                return Column(
                                  children: [
                                    UnderlinedTextField(
                                      label: userState.selectedUser != null
                                          ? AppHelpers.getTranslation(
                                              TrKeys.selectedUser,
                                            )
                                          : AppHelpers.getTranslation(
                                              TrKeys.pleaseSelectAUser,
                                            ),
                                      readOnly: true,
                                      onTap: () async {
                                        await context.pushRoute(
                                          const ManagerSelectUserRoute(),
                                        );
                                      },
                                      textController:
                                          userState.userTextController,
                                      descriptionText:
                                          userState.selectedUser == null
                                          ? null
                                          : userState.selectedUser?.email ?? '',
                                    ),
                                    16.verticalSpace,
                                    if (AppConstants.isSpecificNumberEnabled &&
                                        userState.selectedUser != null)
                                      IntlPhoneField(
                                        disableLengthCheck: !AppConstants
                                            .isNumberLengthAlwaysSame,
                                        onChanged: (phoneNum) {
                                          userNotifier.setPhone(
                                            phoneNum.completeNumber,
                                          );
                                        },
                                        validator: (s) {
                                          if (AppConstants
                                                  .isNumberLengthAlwaysSame &&
                                              (s?.isValidNumber() ?? true)) {
                                            return AppHelpers.getTranslation(
                                              TrKeys.phoneNumberIsNotValid,
                                            );
                                          }
                                          return null;
                                        },
                                        keyboardType: TextInputType.phone,
                                        initialCountryCode:
                                            AppConstants.countryCodeISO,
                                        invalidNumberMessage:
                                            AppHelpers.getTranslation(
                                              TrKeys.phoneNumberIsNotValid,
                                            ),
                                        inputFormatters: [
                                          FilteringTextInputFormatter
                                              .digitsOnly,
                                        ],
                                        showCountryFlag: AppConstants.showFlag,
                                        showDropdownIcon:
                                            AppConstants.showArrowIcon,
                                        autovalidateMode:
                                            AppConstants
                                                .isNumberLengthAlwaysSame
                                            ? AutovalidateMode.onUserInteraction
                                            : AutovalidateMode.disabled,
                                        textAlignVertical:
                                            TextAlignVertical.center,
                                        decoration: InputDecoration(
                                          counterText: '',
                                          enabledBorder: UnderlineInputBorder(
                                            borderSide: BorderSide.merge(
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                            ),
                                          ),
                                          errorBorder: UnderlineInputBorder(
                                            borderSide: BorderSide.merge(
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                            ),
                                          ),
                                          border: const UnderlineInputBorder(),
                                          focusedErrorBorder:
                                              const UnderlineInputBorder(),
                                          disabledBorder: UnderlineInputBorder(
                                            borderSide: BorderSide.merge(
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                              BorderSide(
                                                color:
                                                    AppStyle.differBorderColor,
                                              ),
                                            ),
                                          ),
                                          focusedBorder:
                                              const UnderlineInputBorder(),
                                        ),
                                      ),
                                    if (!AppConstants.isSpecificNumberEnabled &&
                                        userState.selectedUser != null)
                                      UnderlinedTextField(
                                        label: TrKeys.phoneNumber,
                                        textController: _userTextController,
                                        onChanged: (value) =>
                                            userNotifier.setPhone(value),
                                      ),
                                  ],
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    if (deliveryState.type == TrKeys.delivery)
                      Container(
                        margin: REdgeInsets.only(bottom: 12),
                        decoration: BoxDecoration(
                          color: AppStyle.white,
                          borderRadius: BorderRadius.only(
                            bottomLeft: Radius.circular(10.r),
                            bottomRight: Radius.circular(10.r),
                          ),
                        ),
                        padding: REdgeInsets.symmetric(
                          vertical: 24,
                          horizontal: 16,
                        ),
                        child: Consumer(
                          builder: (context, ref, child) {
                            final addressEvent = ref.read(
                              orderAddressProvider.notifier,
                            );
                            final addressState = ref.watch(
                              orderAddressProvider,
                            );
                            return Column(
                              children: [
                                TitleAndIcon(
                                  title: AppHelpers.getTranslation(
                                    TrKeys.shippingAddress,
                                  ),
                                ),
                                24.verticalSpace,
                                Row(
                                  children: [
                                    Expanded(
                                      child: UnderlinedTextField(
                                        label: AppHelpers.getTranslation(
                                          TrKeys.selectedAddress,
                                        ),
                                        textController:
                                            addressState.textController,
                                        readOnly: true,
                                      ),
                                    ),
                                    10.horizontalSpace,
                                    ButtonsBouncingEffect(
                                      child: GestureDetector(
                                        onTap: () => context.pushRoute(
                                          const ManagerSelectAddressRoute(),
                                        ),
                                        child: Container(
                                          width: 40.r,
                                          height: 40.r,
                                          // Not const: AppStyle.primary is
                                          // a getter (brand-injectable).
                                          decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            color: AppStyle.primary,
                                          ),
                                          alignment: Alignment.center,
                                          child: Icon(
                                            Remix.map_pin_add_fill,
                                            size: 24.r,
                                            color: AppStyle.blackColor,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                24.verticalSpace,
                                Row(
                                  children: [
                                    Expanded(
                                      child: UnderlinedTextField(
                                        label: AppHelpers.getTranslation(
                                          TrKeys.entrance,
                                        ),
                                        onChanged: addressEvent.setEntrance,
                                      ),
                                    ),
                                    8.horizontalSpace,
                                    Expanded(
                                      child: UnderlinedTextField(
                                        label: AppHelpers.getTranslation(
                                          TrKeys.floor,
                                        ),
                                        onChanged: addressEvent.setFloor,
                                      ),
                                    ),
                                    8.horizontalSpace,
                                    Expanded(
                                      child: UnderlinedTextField(
                                        label: AppHelpers.getTranslation(
                                          TrKeys.house,
                                        ),
                                        onChanged: addressEvent.setHouse,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            );
                          },
                        ),
                      ),
                    if (deliveryState.type == TrKeys.dineIn)
                      Consumer(
                        builder: (context, ref, child) {
                          final state = ref.watch(sectionProvider);
                          final tableState = ref.watch(tableProvider);
                          return Container(
                            margin: REdgeInsets.only(bottom: 10),
                            decoration: BoxDecoration(
                              color: AppStyle.white,
                              borderRadius: BorderRadius.circular(10.r),
                            ),
                            padding: REdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 24,
                            ),
                            child: Column(
                              children: [
                                TitleAndIcon(
                                  title: AppHelpers.getTranslation(
                                    TrKeys.selectTable,
                                  ),
                                ),
                                16.verticalSpace,
                                UnderlinedTextField(
                                  label: state.selectSection != null
                                      ? AppHelpers.getTranslation(
                                          TrKeys.selectedSection,
                                        )
                                      : AppHelpers.getTranslation(
                                          TrKeys.pleaseSelectASection,
                                        ),
                                  readOnly: true,
                                  onTap: () => context.pushRoute(
                                    const ManagerSelectSectionRoute(),
                                  ),
                                  textController: state.textController,
                                  descriptionText: state.selectSection == null
                                      ? null
                                      : state
                                                .selectSection
                                                ?.translation
                                                ?.description ??
                                            '',
                                ),
                                4.verticalSpace,
                                UnderlinedTextField(
                                  label: tableState.selectTable != null
                                      ? AppHelpers.getTranslation(
                                          TrKeys.selectedTable,
                                        )
                                      : AppHelpers.getTranslation(
                                          TrKeys.pleaseSelectATable,
                                        ),
                                  readOnly: true,
                                  onTap: () {
                                    if (state.selectSection == null) return;
                                    context.pushRoute(
                                      ManagerSelectTableRoute(
                                        sectionId: state.selectSection?.id,
                                      ),
                                    );
                                  },
                                  textController: tableState.textController,
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    78.verticalSpace,
                  ],
                ),
              ),
            );
          },
        ),
        floatingActionButtonLocation:
            FloatingActionButtonLocation.miniCenterDocked,
        floatingActionButton: Padding(
          padding: REdgeInsets.all(16),
          child: Consumer(
            builder: (context, ref, child) => Row(
              children: [
                const PopButton(heroTag: AppConstants.heroTagAddOrderButton),
                8.horizontalSpace,
                if ((ref.watch(deliveryTypeProvider).type == TrKeys.delivery &&
                        ref.watch(orderUserProvider).selectedUser?.phone !=
                            null) ||
                    ref.watch(deliveryTypeProvider).type == TrKeys.pickup ||
                    (ref.watch(deliveryTypeProvider).type == TrKeys.dineIn &&
                        ref.watch(tableProvider).selectTable != null))
                  Expanded(
                    child: CustomButton(
                      title: AppHelpers.getTranslation(TrKeys.next),
                      onPressed: () {
                        if (ref.watch(deliveryTypeProvider).type ==
                            TrKeys.delivery) {
                          if (ref.watch(orderAddressProvider).location ==
                              null) {
                            AppHelpers.showCheckTopSnackBarInfo(
                              context,
                              AppHelpers.getTranslation(TrKeys.selectedAddress),
                            );
                            return;
                          }
                          context.pushRoute(const ManagerDeliveryTimeRoute());
                          return;
                        }
                        context.pushRoute(const ManagerDeliveryTimeRoute());
                      },
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
