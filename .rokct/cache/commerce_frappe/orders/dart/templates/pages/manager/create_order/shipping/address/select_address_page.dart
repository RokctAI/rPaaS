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
import 'package:lottie/lottie.dart' as lottie;
import 'package:google_fonts/google_fonts.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'searched_location_item.dart';
import 'package:${package}/presentation/component/buttons/custom_icon_button.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/services/app_assets.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/address/order/order_address_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/address/select_address_provider.dart';

@RoutePage(name: 'ManagerSelectAddressRoute')
class SelectAddressPage extends StatefulWidget {
  const SelectAddressPage({super.key});

  @override
  State<SelectAddressPage> createState() => _SelectAddressPageState();
}

class _SelectAddressPageState extends State<SelectAddressPage>
    with TickerProviderStateMixin {
  late AnimationController _animationController;
  CameraPosition? _cameraPosition;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(vsync: this);
  }

  @override
  void dispose() {
    super.dispose();
    _animationController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Scaffold(
        backgroundColor: AppStyle.bgGrey,
        resizeToAvoidBottomInset: false,
        body: Consumer(
          builder: (context, ref, child) {
            final state = ref.watch(selectAddressProvider);
            final event = ref.read(selectAddressProvider.notifier);
            return Stack(
              children: [
                GoogleMap(
                  tiltGesturesEnabled: false,
                  myLocationButtonEnabled: false,
                  zoomControlsEnabled: false,
                  initialCameraPosition: CameraPosition(
                    bearing: 0,
                    target: LatLng(
                      AppHelpers.getInitialLatitude() ??
                          AppConstants.demoLatitude,
                      AppHelpers.getInitialLongitude() ??
                          AppConstants.demoLongitude,
                    ),
                    tilt: 0,
                    zoom: 17,
                  ),
                  onMapCreated: (controller) {
                    event.setMapController(controller);
                  },
                  onCameraMoveStarted: () {
                    _animationController.repeat(
                      min: AppConstants.pinLoadingMin,
                      max: AppConstants.pinLoadingMax,
                      period:
                          _animationController.duration! *
                          (AppConstants.pinLoadingMax -
                              AppConstants.pinLoadingMin),
                    );
                    event.setChoosing(true);
                  },
                  onCameraIdle: () {
                    event.fetchLocationName(_cameraPosition?.target);
                    _animationController.forward(
                      from: AppConstants.pinLoadingMax,
                    );
                    event.setChoosing(false);
                  },
                  onCameraMove: (cameraPosition) {
                    _cameraPosition = cameraPosition;
                  },
                ),
                IgnorePointer(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 78.0),
                      child: lottie.Lottie.asset(
                        AppAssets.lottiePin,
                        onLoaded: (composition) {
                          _animationController.duration = composition.duration;
                        },
                        controller: _animationController,
                        width: 250,
                        height: 250,
                      ),
                    ),
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    54.verticalSpace,
                    Container(
                      height: 50.r,
                      padding: REdgeInsets.symmetric(horizontal: 16),
                      margin: REdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        boxShadow: const <BoxShadow>[
                          BoxShadow(
                            color: AppStyle.redBg,
                            offset: Offset(0, 2),
                            blurRadius: 2,
                            spreadRadius: 0,
                          ),
                        ],
                        color: AppStyle.white,
                        borderRadius: BorderRadius.circular(25.r),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Remix.search_line,
                            size: 20.r,
                            color: AppStyle.icons,
                          ),
                          12.horizontalSpace,
                          Expanded(
                            child: TextFormField(
                              controller: state.textController,
                              style: GoogleFonts.inter(
                                fontWeight: FontWeight.w400,
                                fontSize: 14.sp,
                                color: AppStyle.icons,
                                letterSpacing: -0.5,
                              ),
                              onChanged: (value) {
                                event.setQuery(context);
                              },
                              cursorWidth: 1.r,
                              cursorColor: AppStyle.blackColor,
                              decoration: InputDecoration.collapsed(
                                hintText: AppHelpers.getTranslation(
                                  TrKeys.searchLocation,
                                ),
                                hintStyle: GoogleFonts.inter(
                                  fontWeight: FontWeight.w400,
                                  fontSize: 14.sp,
                                  color: const Color(
                                    0xFFC4C4C4,
                                  ) /* legacy Style.iconColor */,
                                  letterSpacing: -0.5,
                                ),
                              ),
                            ),
                          ),
                          IconButton(
                            onPressed: event.clearSearchField,
                            splashRadius: 20.r,
                            padding: EdgeInsets.zero,
                            icon: Icon(
                              Remix.close_line,
                              size: 20.r,
                              color: AppStyle.icons,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (state.isSearching)
                      Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(15.r),
                          color: AppStyle.white,
                        ),
                        margin: REdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 6,
                        ),
                        padding: REdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 10,
                        ),
                        child: ListView.builder(
                          physics: const BouncingScrollPhysics(),
                          shrinkWrap: true,
                          itemCount: state.searchedPlaces.length,
                          padding: EdgeInsets.zero,
                          itemBuilder: (context, index) {
                            return SearchedLocationItem(
                              place: state.searchedPlaces[index],
                              isLast: state.searchedPlaces.length - 1 == index,
                              onTap: () {
                                FocusManager.instance.primaryFocus?.unfocus();
                                event.goToLocation(
                                  place: state.searchedPlaces[index],
                                );
                              },
                            );
                          },
                        ),
                      ),
                  ],
                ),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 150),
                  bottom: state.isChoosing ? -60.r : 20.r,
                  left: 15.r,
                  right: 15.r,
                  child: Row(
                    children: [
                      const PopButton(
                        heroTag: AppConstants.heroTagAddOrderButton,
                      ),
                      8.horizontalSpace,
                      Expanded(
                        child: Consumer(
                          builder: (context, ref, child) {
                            return CustomButton(
                              title: AppHelpers.getTranslation(
                                TrKeys.confirmLocation,
                              ),
                              onPressed: state.location == null
                                  ? null
                                  : () {
                                      ref
                                          .read(orderAddressProvider.notifier)
                                          .setLocation(
                                            title:
                                                state.textController?.text ??
                                                '',
                                            location: state.location,
                                          );
                                      context.maybePop();
                                    },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 150),
                  bottom: 89.r,
                  right: state.isChoosing ? -60.r : 15.r,
                  child: CustomIconButton(
                    iconData: Remix.navigation_fill,
                    size: 60,
                    onTap: event.findMyLocation,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
