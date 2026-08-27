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
import 'package:flutter/rendering.dart';
import 'package:auto_route/auto_route.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'widgets/logout_button.dart';
import 'widgets/logout_modal.dart';
import 'widgets/sections_item.dart';
import 'widgets/shop_page_banner.dart';
import 'widgets/edit_restaurant_modal.dart';
import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:merchants_sdk/src/manager/application/main/main_provider.dart';
import 'package:merchants_sdk/src/manager/application/restaurant/restaurant_provider.dart';
import 'package:merchants_sdk/src/manager/utils/restaurant_helpers.dart';

// Ported from paas_manager lib/presentation/pages/restaurant/
// restaurant_page.dart (main@76b9e9c), with the missing `],` closing the
// body Stack's children restored — the source file on main does not parse.
//
// Tab-hosted: the merchants home shell (pages/main/main_page.dart) imports
// this page directly, so it carries no @RoutePage and the manifest declares
// no route for it (same contract as orders_sdk's OrdersHomePage).
//
// Route call-sites route to the OWNING SDKs' installed pages:
// ManagerIncomeRoute (revenue_sdk), ManagerOrderHistoryRoute (orders_sdk).
// NotificationListRoute stays a HOST route until the comms_sdk consume
// repoints it (fork plan S-3/H-10).
class RestaurantPage extends ConsumerStatefulWidget {
  const RestaurantPage({super.key});

  @override
  ConsumerState<RestaurantPage> createState() => _RestaurantPageState();
}

class _RestaurantPageState extends ConsumerState<RestaurantPage> {
  final ScrollController _controller = ScrollController();

  @override
  void initState() {
    super.initState();
    _controller.addListener(() => listen(_controller));
    // The legacy app fetched the shop at splash/login; in the composed app
    // those flows are host-owned and may not know this provider, so the tab
    // fetches lazily when it has no shop yet.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (ref.read(restaurantProvider).shop == null) {
        ref.read(restaurantProvider.notifier).fetchMyShop();
      }
    });
  }

  @override
  void dispose() {
    super.dispose();
    _controller.removeListener(() => listen(_controller));
  }

  void listen(ScrollController controller) {
    final direction = controller.position.userScrollDirection;
    if (direction == ScrollDirection.reverse) {
      ref.read(mainProvider.notifier).changeScrolling(true);
    } else if (direction == ScrollDirection.forward) {
      ref.read(mainProvider.notifier).changeScrolling(false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: AppStyle.white,
      body: Stack(
        children: [
          CustomScrollView(
            physics: const BouncingScrollPhysics(),
            controller: _controller,
            slivers: <Widget>[
              const ShopBanner(),
              SliverList(
                delegate: SliverChildListDelegate([
                  Consumer(
                    builder: (context, ref, child) {
                      final state = ref.watch(restaurantProvider);
                      // base_sdk keeps the shop as raw JSON; typed state
                      // first, cached JSON as fallback (legacy read the
                      // typed LocalStorage.getShop()).
                      final shopJson = LocalStorage.getShopJson();
                      return ListView(
                        physics: const NeverScrollableScrollPhysics(),
                        padding: REdgeInsets.only(
                          right: 16,
                          left: 16,
                          bottom: MediaQuery.paddingOf(context).bottom,
                        ),
                        shrinkWrap: true,
                        children: [
                          Row(
                            children: [
                              Text(
                                RestaurantHelpers.truncate(
                                  state.shop?.translation?.title ??
                                      (shopJson?['translation']?['title']
                                          as String?) ??
                                      "",
                                  16,
                                ),
                                style: AppStyle.interSemi(
                                  size: 22.sp,
                                  color: AppStyle.blackColor,
                                ),
                              ),
                              Container(
                                width: 4.w,
                                height: 4.h,
                                margin: REdgeInsets.symmetric(horizontal: 8),
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppStyle.textGrey,
                                ),
                              ),
                              Icon(
                                Remix.star_smile_fill,
                                color: AppStyle.starColor,
                                size: 20.r,
                              ),
                              4.horizontalSpace,
                              Text(
                                state.shop?.avgRate ?? '0.0',
                                style: AppStyle.interNormal(
                                  size: 12.sp,
                                  color: AppStyle.blackColor,
                                ),
                              ),
                              const Spacer(),
                              Container(
                                width: 22.w,
                                height: 22.h,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppStyle.red,
                                ),
                                child: Icon(
                                  Remix.percent_fill,
                                  color: AppStyle.white,
                                  size: 12.r,
                                ),
                              ),
                              14.horizontalSpace,
                              Container(
                                width: 22.w,
                                height: 22.h,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppStyle.primary,
                                ),
                                child: Icon(Remix.flashlight_fill, size: 16.r),
                              ),
                            ],
                          ),
                          Text(
                            '${state.shop?.translation?.description}',
                            style: AppStyle.interNormal(
                              size: 13.sp,
                              color: AppStyle.blackColor,
                            ),
                          ),
                          Container(
                            height: 46.r,
                            margin: EdgeInsets.only(top: 24.h, bottom: 10.h),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(10.r),
                              border: Border.all(
                                color: AppStyle.borderColor,
                                width: 1.r,
                              ),
                            ),
                            alignment: Alignment.center,
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Remix.time_fill,
                                  size: 20.r,
                                  color: AppStyle.blackColor,
                                ),
                                10.horizontalSpace,
                                Builder(
                                  builder: (context) {
                                    final todayTime =
                                        RestaurantHelpers.workingTimeForToday(
                                          state.shop,
                                        );
                                    return RichText(
                                      text: TextSpan(
                                        text: todayTime == null
                                            ? ''
                                            : '${AppHelpers.getTranslation(TrKeys.workingHours)}:',
                                        style: AppStyle.interRegular(
                                          color: AppStyle.blackColor,
                                          size: 12.sp,
                                        ),
                                        children: [
                                          TextSpan(
                                            text:
                                                ' ${todayTime ?? AppHelpers.getTranslation(TrKeys.theRestaurantIsClosedToday)}',
                                            style: AppStyle.interSemi(
                                              color: AppStyle.blackColor,
                                              size: 13.sp,
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                              ],
                            ),
                          ),
                          Container(
                            height: 74.r,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(10.r),
                              border: Border.all(color: AppStyle.borderColor),
                            ),
                            alignment: Alignment.center,
                            child: Padding(
                              padding: REdgeInsets.symmetric(horizontal: 24),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Remix.coins_fill,
                                    size: 45.r,
                                    color: AppStyle.blackColor,
                                  ),
                                  10.horizontalSpace,
                                  Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        AppHelpers.getTranslation(
                                          TrKeys.balance,
                                        ),
                                        style: AppStyle.interNormal(
                                          size: 14.sp,
                                          color: AppStyle.blackColor,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                      Text(
                                        // Recorded backend gap: get_shop
                                        // returns no seller wallet yet, so
                                        // this reads the raw cached JSON
                                        // (degrades to 0, nothing faked).
                                        AppHelpers.numberFormat(
                                          number:
                                              shopJson?['seller']?['wallet']?['price']
                                                  as num?,
                                          symbol:
                                              shopJson?['seller']?['wallet']?['symbol']
                                                  as String?,
                                        ),
                                        style: AppStyle.interSemi(
                                          size: 18.sp,
                                          color: AppStyle.blackColor,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const Spacer(),
                                  Container(
                                    width: 1.r,
                                    height: 46.r,
                                    color: AppStyle.blackColor.withOpacity(0.1),
                                  ),
                                  const Spacer(),
                                  Icon(
                                    Remix.bar_chart_line,
                                    size: 24.r,
                                    color: AppStyle.blackColor,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          16.verticalSpace,
                          _sections(context),
                        ],
                      );
                    },
                  ),
                ]),
              ),
            ],
          ),
          Consumer(
            builder: (context, ref, child) {
              return LogoutButton(
                isOpen: ref.watch(restaurantProvider).shop?.open ?? false,
                onChange: () {
                  ref.read(restaurantProvider.notifier).setOnlineOffline();
                },
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _sections(BuildContext context) {
    return Column(
      children: [
        TitleAndIcon(title: AppHelpers.getTranslation(TrKeys.sections)),
        20.verticalSpace,
        SectionsItem(
          title: AppHelpers.getTranslation(TrKeys.restaurantSettings),
          icon: Remix.restaurant_line,
          onTap: () => AppHelpers.showCustomModalBottomSheet(
            paddingTop: MediaQuery.paddingOf(context).top + 60,
            context: context,
            modal: const EditRestaurantModal(),
            isDarkMode: false,
          ),
        ),
        SectionsItem(
          title: AppHelpers.getTranslation(TrKeys.income),
          icon: Remix.line_chart_line,
          onTap: () => context.pushRoute(const ManagerIncomeRoute()),
        ),
        SectionsItem(
          title: AppHelpers.getTranslation(TrKeys.myOrderHistory),
          icon: Remix.history_line,
          onTap: () => context.pushRoute(const ManagerOrderHistoryRoute()),
        ),
        SectionsItem(
          title: AppHelpers.getTranslation(TrKeys.notifications),
          icon: Remix.notification_2_line,
          onTap: () => context.pushRoute(const NotificationListRoute()),
        ),
        // Park-and-surface: records whose offline push the backend rejected,
        // with per-record retry/discard (merchants_sdk's own installed page).
        SectionsItem(
          title: AppHelpers.getTranslation(TrKeys.syncIssues),
          icon: Remix.refresh_line,
          onTap: () => context.pushRoute(const ManagerSyncIssuesRoute()),
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
    );
  }
}
