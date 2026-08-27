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

import 'package:auto_route/annotations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:lottie/lottie.dart';
import 'package:map_launcher/map_launcher.dart';
import 'package:remixicon/remixicon.dart';

import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

import 'package:delivery_sdk/src/driver/application/route/route_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/models/data/route_stop.dart';

import 'package:${package}/presentation/component/maps_list.dart';

/// The driver's numbered, server-ordered route: active order and parcel
/// stops merged with the pending stops of an admin-composed Dispatch
/// Route. The driver just drives stop to stop — the backend decides the
/// order (nearest-next, pickups before their drop-offs) and re-orders
/// after every completion.
@RoutePage()
class DriverRoutePage extends ConsumerStatefulWidget {
  const DriverRoutePage({super.key});

  @override
  ConsumerState<DriverRoutePage> createState() => _DriverRoutePageState();
}

class _DriverRoutePageState extends ConsumerState<DriverRoutePage> {
  @override
  void initState() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(routeProvider.notifier).fetchRoute(context);
    });
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(routeProvider);
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          CustomAppBar(
            bottomPadding: 16.h,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  AppHelpers.getTranslation(TrKeys.myRoute),
                  style: AppStyle.interSemi(size: 18.sp),
                ),
                if (state.dispatchRoute != null)
                  Text(
                    "${AppHelpers.getTranslation(state.dispatchRoute?.mode == 'Pickup' ? TrKeys.pickupRoute : TrKeys.deliveryRoute)}"
                    " · ${state.dispatchRoute?.pendingStops ?? 0}/${state.dispatchRoute?.totalStops ?? 0}",
                    style: AppStyle.interRegular(
                      size: 12.sp,
                      letterSpacing: -0.3,
                    ),
                  ),
              ],
            ),
          ),
          if ((state.dispatchRoute?.notes ?? '').isNotEmpty)
            Padding(
              padding: EdgeInsets.only(left: 16.w, right: 16.w, top: 12.h),
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  color: AppStyle.white,
                  borderRadius: BorderRadius.circular(10.r),
                ),
                padding: EdgeInsets.all(12.r),
                child: Text(
                  state.dispatchRoute?.notes ?? '',
                  style: AppStyle.interRegular(size: 13.sp),
                ),
              ),
            ),
          Expanded(
            child: state.isLoading
                ? const Loading()
                : RefreshIndicator(
                    onRefresh: () =>
                        ref.read(routeProvider.notifier).fetchRoute(context),
                    child: state.stops.isEmpty
                        ? _emptyRoute()
                        : ListView.builder(
                            padding: EdgeInsets.only(
                              left: 16.w,
                              right: 16.w,
                              top: 16.h,
                              bottom:
                                  MediaQuery.paddingOf(context).bottom + 72.h,
                            ),
                            physics: const AlwaysScrollableScrollPhysics(),
                            itemCount: state.stops.length,
                            itemBuilder: (context, index) {
                              return _stopCard(
                                context,
                                state.stops[index],
                                isNext: index == state.nextStopIndex,
                                isCompleting: state.isCompleting,
                              );
                            },
                          ),
                  ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      floatingActionButton: const PopButton(),
    );
  }

  Widget _emptyRoute() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        16.verticalSpace,
        Lottie.asset("assets/lottie/empty-box.json"),
        Text(
          AppHelpers.getTranslation(TrKeys.noRouteStops),
          style: AppStyle.interSemi(size: 18.sp),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _stopCard(
    BuildContext context,
    RouteStopData stop, {
    required bool isNext,
    required bool isCompleting,
  }) {
    final isDone = !stop.isPending;
    return GestureDetector(
      onTap: () => _openInMaps(context, stop),
      child: Container(
        margin: EdgeInsets.only(bottom: 10.h),
        decoration: BoxDecoration(
          color: AppStyle.white,
          borderRadius: BorderRadius.circular(10.r),
          border: isNext
              ? Border.all(color: AppStyle.primary, width: 2.r)
              : null,
        ),
        padding: EdgeInsets.all(14.r),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32.r,
                  height: 32.r,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isDone
                        ? AppStyle.unselectedTab
                        : (isNext ? AppStyle.primary : AppStyle.black),
                  ),
                  child: Text(
                    "${stop.sequence ?? ''}",
                    style: AppStyle.interBold(
                      size: 14,
                      color: isNext && !isDone
                          ? AppStyle.black
                          : AppStyle.white,
                    ),
                  ),
                ),
                12.horizontalSpace,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stop.label ?? stop.refName ?? '',
                        style: AppStyle.interSemi(size: 14.sp),
                      ),
                      4.verticalSpace,
                      Row(
                        children: [
                          Icon(
                            stop.stopType == 'pickup'
                                ? Remix.store_2_line
                                : Remix.map_pin_2_line,
                            size: 14.sp,
                            color: AppStyle.textGrey,
                          ),
                          4.horizontalSpace,
                          Text(
                            AppHelpers.getTranslation(stop.stopType ?? ''),
                            style: AppStyle.interRegular(
                              size: 12.sp,
                              color: AppStyle.textGrey,
                            ),
                          ),
                          if (stop.distanceFromPreviousKm != null) ...[
                            8.horizontalSpace,
                            Icon(
                              Remix.route_line,
                              size: 14.sp,
                              color: AppStyle.textGrey,
                            ),
                            4.horizontalSpace,
                            Text(
                              "${stop.distanceFromPreviousKm} ${AppHelpers.getTranslation(TrKeys.km)}",
                              style: AppStyle.interRegular(
                                size: 12.sp,
                                color: AppStyle.textGrey,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                if (stop.hasCoordinates)
                  Icon(
                    Remix.navigation_fill,
                    size: 18.sp,
                    color: AppStyle.primary,
                  ),
              ],
            ),
            if (stop.quantity != null) ...[
              10.verticalSpace,
              Row(
                children: [
                  Icon(Remix.drop_fill, size: 16.sp, color: AppStyle.primary),
                  6.horizontalSpace,
                  Text(
                    "${AppHelpers.getTranslation(TrKeys.quantity)}: ${stop.quantity} ${stop.unit ?? ''}",
                    style: AppStyle.interSemi(size: 13.sp),
                  ),
                ],
              ),
            ],
            if ((stop.paymentTag ?? '').toLowerCase() == 'cash') ...[
              8.verticalSpace,
              Row(
                children: [
                  Icon(
                    Remix.money_dollar_circle_fill,
                    size: 16.sp,
                    color: AppStyle.primary,
                  ),
                  6.horizontalSpace,
                  Text(
                    "${AppHelpers.getTranslation(TrKeys.cashToCollect)}${stop.totalPrice != null ? ": ${AppHelpers.numberFormat(number: stop.totalPrice)}" : ""}",
                    style: AppStyle.interSemi(
                      size: 13.sp,
                      color: AppStyle.primary,
                    ),
                  ),
                ],
              ),
            ],
            if (stop.missingCoordinates) ...[
              8.verticalSpace,
              Text(
                AppHelpers.getTranslation(TrKeys.noLocationForStop),
                style: AppStyle.interRegular(
                  size: 12.sp,
                  color: AppStyle.textGrey,
                ),
              ),
            ],
            if (stop.isDispatchStop && stop.isPending) ...[
              12.verticalSpace,
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppStyle.primary,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10.r),
                        ),
                      ),
                      onPressed: isCompleting
                          ? null
                          : () => _completeStop(context, stop, 'Done'),
                      child: Text(
                        AppHelpers.getTranslation(TrKeys.done),
                        style: AppStyle.interSemi(
                          size: 13.sp,
                          color: AppStyle.black,
                        ),
                      ),
                    ),
                  ),
                  10.horizontalSpace,
                  Expanded(
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10.r),
                        ),
                      ),
                      onPressed: isCompleting
                          ? null
                          : () => _completeStop(context, stop, 'Skipped'),
                      child: Text(
                        AppHelpers.getTranslation(TrKeys.skip),
                        style: AppStyle.interSemi(
                          size: 13.sp,
                          color: AppStyle.black,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _completeStop(BuildContext context, RouteStopData stop, String status) {
    final routeId = stop.routeId;
    final stopName = stop.refName;
    if (routeId == null || stopName == null) return;
    ref
        .read(routeProvider.notifier)
        .completeStop(
          context,
          routeId: routeId,
          stopName: stopName,
          status: status,
        );
  }

  void _openInMaps(BuildContext context, RouteStopData stop) {
    if (!stop.hasCoordinates) return;
    AppHelpers.showCustomModalBottomSheet(
      context: context,
      modal: SafeArea(
        child: Padding(
          padding: EdgeInsets.only(top: 16.h),
          child: MapsList(
            location: Coords(stop.latitude ?? 0, stop.longitude ?? 0),
            title: stop.label ?? '',
          ),
        ),
      ),
      isDarkMode: false,
    );
  }
}
