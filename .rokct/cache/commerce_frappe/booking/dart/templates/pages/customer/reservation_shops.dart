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
import 'package:intl/intl.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:base_sdk/src/application/home/home_provider.dart';
import 'package:base_sdk/src/application/select/select_provider.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:base_sdk/src/presentation/components/buttons/animation_button_effect.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/custom_network_image.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:url_launcher/url_launcher.dart';

class ReservationShops extends ConsumerStatefulWidget {
  const ReservationShops({super.key});

  @override
  ConsumerState<ReservationShops> createState() => _ReservationShopsState();
}

class _ReservationShopsState extends ConsumerState<ReservationShops> {
  final RefreshController _recommendedController = RefreshController();

  @override
  void initState() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(homeProvider.notifier).fetchShop(context);
      ref.read(selectProvider.notifier).selectIndex(0);
    });
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final event = ref.read(homeProvider.notifier);
    final state = ref.watch(homeProvider);
    final selectState = ref.watch(selectProvider);
    return SizedBox(
      height: 480.r,
      width: MediaQuery.sizeOf(context).width / 1.4,
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  AppHelpers.getTranslation(TrKeys.shop),
                  style: AppStyle.interNoSemi(
                    size: 16,
                    color: AppStyle.black,
                  ),
                ),
              ),
              GestureDetector(
                onTap: () => Navigator.pop(context),
                child: const Icon(Icons.close),
              ),
            ],
          ),
          Expanded(
            child: SmartRefresher(
              controller: _recommendedController,
              enablePullDown: true,
              enablePullUp: true,
              onLoading: () async {
                await event.fetchShopPage(context, _recommendedController);
              },
              onRefresh: () async {
                await event.fetchShopPage(
                  context,
                  _recommendedController,
                  isRefresh: true,
                );
              },
              child: ListView.builder(
                itemCount: state.shops.length,
                shrinkWrap: true,
                padding: REdgeInsets.symmetric(vertical: 8),
                itemBuilder: (context, index) {
                  return Padding(
                    padding: REdgeInsets.only(bottom: 8),
                    child: AnimationButtonEffect(
                      child: GestureDetector(
                        onTap: () {
                          ref.read(selectProvider.notifier).selectIndex(index);
                        },
                        child: Container(
                          decoration: BoxDecoration(
                            color: selectState.selectedIndex == index
                                ? AppStyle.primary.withValues(alpha: 0.4)
                                : AppStyle.bgGrey,
                            borderRadius: BorderRadius.circular(8.r),
                            border: Border.all(
                              color: selectState.selectedIndex == index
                                  ? AppStyle.primary
                                  : AppStyle.transparent,
                              width: 1.8,
                            ),
                          ),
                          child: Padding(
                            padding: REdgeInsets.all(8),
                            child: Row(
                              children: [
                                CustomNetworkImage(
                                  url: state.shops[index].logoImg,
                                  height: 48,
                                  width: 48,
                                  radius: 24,
                                ),
                                8.horizontalSpace,
                                Expanded(
                                  child: Text(
                                    state.shops[index].translation?.title ??
                                        ' ',
                                    maxLines: 2,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          CustomButton(
            title: AppHelpers.getTranslation(TrKeys.next),
            onPressed: () async {
              // ignore: deprecated_member_use
              await launch(
                "${AppConstants.webUrl}/reservations/${state.shops[selectState.selectedIndex].id}?guests=2&date_from=${DateFormat("yyyy-MM-dd").format(DateTime.now())}",
                enableJavaScript: true,
              );
            },
          ),
        ],
      ),
    );
  }
}

