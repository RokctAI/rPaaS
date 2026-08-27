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

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:${package}/presentation/pages/profile/courier_statistics_provider.dart';
import 'package:${package}/presentation/pages/profile/widgets/edit_profile_modal.dart';

import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

import 'package:${package}/presentation/pages/profile/widgets/logout_modal.dart';
import 'package:${package}/presentation/pages/profile/widgets/sections_item.dart';
import 'package:${package}/presentation/component/buttons/buttons_bouncing_effect.dart';
import 'package:${package}/presentation/component/driver_avatar.dart';
import 'package:base_sdk/src/application/app_widget/app_provider.dart';
import 'package:base_sdk/src/navigation/embedded_widgets.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/services/app_assets.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_image_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_settings_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_constants.dart';

@RoutePage()
class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  final bool isLtr = LocalStorage.getLangLtr();

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileSettingsProvider);
    ref.watch(appProvider);
    return Directionality(
      textDirection: isLtr ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppStyle.bgGrey,
        resizeToAvoidBottomInset: false,
        body: Column(
          children: [
            CustomAppBar(
              bottomPadding: 4.h,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisAlignment: MainAxisAlignment.start,
                children: [
                  Hero(
                    tag: CourierConstants.heroTagProfileAvatar,
                    child: Consumer(
                      builder: (context, ref, child) {
                        ref.watch(profileImageProvider);
                        return DriverAvatar(
                          imageUrl: LocalStorage.getUser()?.img,
                          rate: LocalStorage.getUser()?.rate,
                        );
                      },
                    ),
                  ),
                  10.horizontalSpace,
                  Padding(
                    padding: EdgeInsets.only(bottom: 24.h),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text(
                          '${LocalStorage.getUser()?.firstname ?? ''} ${LocalStorage.getUser()?.lastname ?? ''}',
                          style: AppStyle.interSemi(size: 16.sp),
                        ),
                        Text(
                          LocalStorage.getUser()?.phone ?? '',
                          style: AppStyle.interRegular(size: 12.sp),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  Padding(
                    padding: EdgeInsets.only(bottom: 24.h),
                    child: ButtonsBouncingEffect(
                      child: GestureDetector(
                        onTap: () {
                          AppHelpers.showCustomModalBottomSheet(
                            context: context,
                            modal: const LogoutModal(),
                            isDarkMode: LocalStorage.getAppThemeMode(),
                          );
                        },
                        child: Icon(
                          Remix.logout_circle_r_line,
                          size: 24.r,
                          color: AppStyle.black,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 24.h),
                shrinkWrap: true,
                physics: const BouncingScrollPhysics(),
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: AppStyle.white,
                      borderRadius: BorderRadius.circular(10.r),
                    ),
                    padding: EdgeInsets.all(12.r),
                    child: IntrinsicHeight(
                      child: Row(
                        children: [
                          SvgPicture.asset(AppAssets.svgBalance),
                          10.horizontalSpace,
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                AppHelpers.getTranslation(TrKeys.balance),
                                style: AppStyle.interNormal(
                                  size: 12.sp,
                                  letterSpacing: -0.3,
                                ),
                              ),
                              Text(
                                AppHelpers.numberFormat(
                                  number: LocalStorage.getUser()?.wallet?.price,
                                ),
                                style: AppStyle.interSemi(
                                  size: 14.sp,
                                  letterSpacing: -0.3,
                                ),
                              ),
                            ],
                          ),
                          const Spacer(),
                          const VerticalDivider(color: AppStyle.borderColor),
                          10.horizontalSpace,
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                AppHelpers.getTranslation(TrKeys.lastProfit),
                                style: AppStyle.interNormal(
                                  size: 12.sp,
                                  letterSpacing: -0.3,
                                ),
                              ),
                              Text(
                                AppHelpers.numberFormat(
                                  number:
                                      ref
                                          .watch(
                                            courierProfileStatisticsProvider,
                                          )
                                          .statistics
                                          ?.data
                                          ?.totalPrice ??
                                      0,
                                ),
                                style: AppStyle.interSemi(
                                  size: 14.sp,
                                  letterSpacing: -0.3,
                                  color: AppStyle.primary,
                                ),
                              ),
                            ],
                          ),
                          32.horizontalSpace,
                        ],
                      ),
                    ),
                  ),
                  10.verticalSpace,
                  Container(
                    decoration: BoxDecoration(
                      color: AppStyle.white,
                      borderRadius: BorderRadius.circular(10.r),
                    ),
                    padding: EdgeInsets.all(12.r),
                    child: Row(
                      children: [
                        Icon(Remix.checkbox_circle_fill, size: 30.r),
                        10.horizontalSpace,
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              AppHelpers.getTranslation(TrKeys.deliveredOrder),
                              style: AppStyle.interNormal(
                                size: 12.sp,
                                letterSpacing: -0.3,
                              ),
                            ),
                            Text(
                              (ref
                                          .watch(
                                            courierProfileStatisticsProvider,
                                          )
                                          .statistics
                                          ?.data
                                          ?.deliveredOrdersCount ??
                                      0)
                                  .toString(),
                              style: AppStyle.interSemi(
                                size: 14.sp,
                                letterSpacing: -0.3,
                              ),
                            ),
                          ],
                        ),
                        const Spacer(),
                        10.horizontalSpace,
                        // if( state.requestData?.status ==
                        //     TrKeys.canceled)
                        // ButtonsBouncingEffect(
                        //   child: InkWell(
                        //     onTap: () {
                        //       AppHelpers.showAlertDialog(
                        //         context: context,
                        //         child:  CancelDialog(note: state.requestData?.statusNote ?? "",),
                        //       );
                        //     },
                        //     child: Row(
                        //       children: [
                        //         Icon(
                        //           Remix.close_circle_line,
                        //           size: 30.r,
                        //           color: AppStyle.red,
                        //         ),
                        //         10.horizontalSpace,
                        //         Column(
                        //           crossAxisAlignment: CrossAxisAlignment.start,
                        //           children: [
                        //             Text(
                        //               AppHelpers.getTranslation(
                        //                   TrKeys.youStatus),
                        //               style: AppStyle.interNormal(
                        //                 size: 12.sp,
                        //                 letterSpacing: -0.3,
                        //               ),
                        //             ),
                        //             Text(
                        //               state.requestData?.status ?? '',
                        //               style: AppStyle.interSemi(
                        //                 size: 13.sp,
                        //                 letterSpacing: -0.3,
                        //                 color: state.requestData?.status ==
                        //                         TrKeys.canceled
                        //                     ? AppStyle.red
                        //                     : AppStyle.primary,
                        //               ),
                        //             ),
                        //           ],
                        //         ),
                        //       ],
                        //     ),
                        //   ),
                        // ),
                        24.horizontalSpace,
                      ],
                    ),
                  ),
                  // _notifications(context),
                  20.verticalSpace,
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.profileSettings),
                    icon: Remix.user_settings_line,
                    onTap: () {
                      AppHelpers.showCustomModalBottomSheet(
                        paddingTop: MediaQuery.paddingOf(context).top + 32.h,
                        context: context,
                        modal: const EditProfileModal(),
                        isDarkMode: false,
                      );
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.deliveryZone),
                    icon: Remix.navigation_fill,
                    onTap: () async {
                      await context.pushRoute(const DriverDeliveryZoneRoute());
                      ref
                          .read(homeProvider.notifier)
                          .fetchDeliveryZone(isFetch: true);
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.orders),
                    icon: Remix.order_play_line,
                    onTap: () {
                      context.pushRoute(const OrdersRoute());
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.parcels),
                    icon: Remix.archive_line,
                    onTap: () {
                      context.pushRoute(const ParcelsRoute());
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.notifications),
                    icon: Remix.notification_2_line,
                    onTap: () =>
                        context.pushRoute(const NotificationListRoute()),
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.orderHistory),
                    icon: Remix.history_line,
                    onTap: () {
                      context.pushRoute(const OrderHistoryRoute());
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.parcelHistory),
                    icon: Remix.folder_history_fill,
                    onTap: () {
                      context.pushRoute(const ParcelHistoryRoute());
                    },
                  ),
                  SectionsItem(
                    title: AppHelpers.getTranslation(TrKeys.income),
                    icon: Remix.line_chart_line,
                    onTap: () {
                      context.pushRoute(const DriverIncomeRoute());
                    },
                  ),
                  Consumer(
                    builder: (context, ref, child) {
                      return SectionsItem(
                        title: AppHelpers.getTranslation(TrKeys.language),
                        icon: Remix.global_line,
                        onTap: () {
                          AppHelpers.showCustomModalBottomSheet(
                            isDismissible: true,
                            isDrag: false,
                            context: context,
                            modal: EmbeddedWidgets.I.languageScreen(
                              onSave: () {
                                Navigator.pop(context);
                                ref
                                    .read(appProvider.notifier)
                                    .changeLocale(LocalStorage.getLanguage());
                              },
                            ),
                            isDarkMode: false,
                          );
                        },
                      );
                    },
                  ),
                  if (!AppConstants.isDemo)
                    SectionsItem(
                      title: AppHelpers.getTranslation(TrKeys.deleteAccount),
                      icon: Remix.logout_box_r_line,
                      onTap: () {
                        AppHelpers.showCustomModalBottomSheet(
                          context: context,
                          modal: const LogoutModal(isDeleteAccount: true),
                          isDarkMode: false,
                        );
                      },
                    ),
                  100.verticalSpace,
                ],
              ),
            ),
          ],
        ),
        floatingActionButtonLocation:
            FloatingActionButtonLocation.miniCenterFloat,
        floatingActionButton: Padding(
          padding: REdgeInsets.only(left: 16, right: 16, bottom: 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const PopButton(),
              10.horizontalSpace,
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.onlineHelper),
                  textColor: AppStyle.white,
                  onPressed: () async {
                    final Uri launchUri = Uri(
                      scheme: 'tel',
                      path: AppHelpers.getAppPhone(),
                    );
                    await launchUrl(launchUri);
                  },
                  icon: Icon(
                    Remix.chat_smile_2_fill,
                    color: AppStyle.white,
                    size: 20.r,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Widget _notifications(BuildContext context) {
  //   return Column(
  //     children: [
  //       24.verticalSpace,
  //       Row(
  //         children: [
  //           Container(
  //             decoration: const BoxDecoration(
  //               color: AppStyle.primary,
  //               shape: BoxShape.circle,
  //             ),
  //             height: 30.h,
  //             width: 30.w,
  //             child: Center(
  //               child: Text(
  //                 "4",
  //                 style: AppStyle.interSemi(size: 14.sp, color: AppStyle.blackColor),
  //               ),
  //             ),
  //           ),
  //           12.horizontalSpace,
  //           Text(
  //             AppHelpers.getTranslation(TrKeys.notifications),
  //             style: AppStyle.interSemi(size: 18.sp, color: AppStyle.blackColor),
  //           ),
  //           const Spacer(),
  //           GestureDetector(
  //             onTap: () {
  //               context.pushRoute(const ListNotificationRoute());
  //             },
  //             child: Padding(
  //               padding: const EdgeInsets.all(4.0),
  //               child: Text(
  //                 AppHelpers.getTranslation(TrKeys.seeAll),
  //                 style: AppStyle.interNormal(size: 14.sp, color: AppStyle.blue),
  //               ),
  //             ),
  //           ),
  //         ],
  //       ),
  //       16.verticalSpace,
  //       SizedBox(
  //         height: 136.h,
  //         child: ListView.builder(
  //           scrollDirection: Axis.horizontal,
  //           itemCount: 4,
  //           physics: const BouncingScrollPhysics(),
  //           itemBuilder: (context, index) {
  //             return const NotificationItem(
  //               date: "June 24",
  //               text: "Check your settings you have notifications turned off",
  //             );
  //           },
  //         ),
  //       ),
  //       40.verticalSpace,
  //     ],
  //   );
  // }
}
