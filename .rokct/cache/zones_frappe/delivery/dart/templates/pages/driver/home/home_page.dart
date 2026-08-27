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

import 'dart:async';
import 'dart:convert';
import 'package:auto_route/auto_route.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:delivery_sdk/src/driver/application/order/order_provider.dart';
import 'package:delivery_sdk/src/driver/di/driver_delivery_di.dart';
import 'package:delivery_sdk/src/driver/infrastructure/models/data/order_detail.dart';
import 'package:base_sdk/src/handlers/api_result.dart';
import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:${package}/presentation/pages/home/parcel_bottom_sheet.dart';

import 'package:workmanager/workmanager.dart';

// fetchBackground (the periodic courier-location task id) lives in
// delivery_sdk since driver migration M4 — the generated main.dart no longer
// declares it (the dispatcher is wired by this manifest's boot_hooks entry).
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_location_service.dart';

import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/home/bottom_sheet_screen.dart';
import 'package:${package}/presentation/pages/home/delivery_bottom_sheet.dart';
import 'package:${package}/presentation/component/buttons/buttons_bouncing_effect.dart';
import 'package:${package}/presentation/component/custom_toggle.dart';
import 'package:${package}/presentation/component/driver_avatar.dart';
import 'package:${package}/presentation/pages/push_order/push_order_screen.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/blur_wrap.dart';
import 'package:base_sdk/src/services/app_assets.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/marker_image_cropper.dart';
import 'package:base_sdk/src/services/tpying_delay.dart';
import 'package:delivery_sdk/src/driver/application/driver/driver_provider.dart';
import 'package:delivery_sdk/src/driver/application/home/home_provider.dart';
import 'package:${package}/presentation/pages/profile/courier_statistics_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_image_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_settings_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_constants.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_helpers.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_storage.dart';

@RoutePage()
class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final GeolocatorPlatform _geolocatorPlatform = GeolocatorPlatform.instance;
  final bool isLtr = LocalStorage.getLangLtr();
  GoogleMapController? googleMapController;
  BitmapDescriptor myIcon = BitmapDescriptor.defaultMarker;
  OrderDetailData? push;
  Timer? timer;
  LatLng latLng = LatLng(
    (LocalStorage.getAddressSelected()?.latitude ?? AppConstants.demoLatitude),
    (LocalStorage.getAddressSelected()?.longitude ??
        AppConstants.demoLongitude),
  );
  Position? currentLocation;
  dynamic check;
  final _delayed = Delayed(milliseconds: 36000);

  Future<void> setCustomMarkerIcon() async {
    final Uint8List markerMyIcon = await CourierHelpers.getBytesFromAsset(
      AppAssets.pngMyLocation,
      120,
    );
    myIcon = BitmapDescriptor.fromBytes(markerMyIcon);
  }

  checkPermission() async {
    // firebase_messaging has no Windows/Linux implementation — on desktop
    // Firebase is (correctly) never initialized, so an unguarded
    // FirebaseMessaging.instance throws [core/no-app]. Same platform guard +
    // fail-open idiom as comms' firebase boot hook (defensive: driver is
    // mobile-only today, but this matches the merchants main-page fix).
    if (!kIsWeb &&
        (defaultTargetPlatform == TargetPlatform.android ||
            defaultTargetPlatform == TargetPlatform.iOS ||
            defaultTargetPlatform == TargetPlatform.macOS)) {
      try {
        FirebaseMessaging.instance.requestPermission(
          sound: true,
          alert: true,
          badge: false,
        );

        FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
          debugPrint(
            "New notification on message: ${jsonEncode(message.data)}",
          );
          if (message.data["id"] != null && mounted) {
            AppHelpers.showCheckTopSnackBarInfo(
              context,
              "${message.notification?.body}",
            );
          }
          if (message.data["type"] == "new_order") {
            final res = await orderRepository.showOrders(
              message.data["id"].toString(),
            );
            res.map(
              success: (s) {
                attachOrder(s.data.data);
              },
              failure: (f) {},
            );
          } else if (message.data["type"] == "deliveryman") {
            final res = await orderRepository.showOrders(
              message.data["id"].toString(),
            );
            res.map(
              success: (s) {
                newOrder(s.data.data);
              },
              failure: (f) {},
            );
          }
        });
        FirebaseMessaging.onMessageOpenedApp.listen((
          RemoteMessage message,
        ) async {
          debugPrint("New notification oped app: ${jsonEncode(message.data)}");

          if (message.data["type"] == "new_order") {
            final res = await orderRepository.showOrders(
              message.data["id"].toString(),
            );
            res.map(
              success: (s) {
                attachOrder(s.data.data);
              },
              failure: (f) {},
            );
          } else if (message.data["type"] == "deliveryman") {
            final res = await orderRepository.showOrders(
              message.data["id"].toString(),
            );
            res.map(
              success: (s) {
                newOrder(s.data.data);
              },
              failure: (f) {},
            );
          }
        });
      } catch (e) {
        debugPrint('==> driver home FCM setup skipped: $e');
      }
    }

    check = await _geolocatorPlatform.checkPermission();
    if (check == LocationPermission.denied) {
      check = await Geolocator.requestPermission();
      if (check != LocationPermission.denied &&
          check != LocationPermission.deniedForever) {
        var loc = await Geolocator.getCurrentPosition();
        latLng = LatLng(loc.latitude, loc.longitude);
        CourierStorage.saveSelectedLocation(latLng);
        googleMapController!.animateCamera(
          CameraUpdate.newLatLngZoom(latLng, 15),
        );
      }
    } else {
      if (check != LocationPermission.deniedForever) {
        var loc = await Geolocator.getCurrentPosition();
        latLng = LatLng(loc.latitude, loc.longitude);
        CourierStorage.saveSelectedLocation(latLng);
        googleMapController!.animateCamera(
          CameraUpdate.newLatLngZoom(latLng, 15),
        );
      }
    }
  }

  Future<void> getMyLocation() async {
    if (check == LocationPermission.denied) {
      check = await Geolocator.requestPermission();
      if (check != LocationPermission.denied &&
          check != LocationPermission.deniedForever) {
        var loc = await Geolocator.getCurrentPosition();
        latLng = LatLng(loc.latitude, loc.longitude);
        CourierStorage.saveSelectedLocation(latLng);
        googleMapController!.animateCamera(
          CameraUpdate.newLatLngZoom(latLng, 15),
        );
      }
    } else {
      if (check != LocationPermission.deniedForever) {
        var loc = await Geolocator.getCurrentPosition();
        latLng = LatLng(loc.latitude, loc.longitude);
        CourierStorage.saveSelectedLocation(latLng);
        googleMapController!.animateCamera(
          CameraUpdate.newLatLngZoom(latLng, 15),
        );
      }
    }
  }

  void getSetProgressLocation() {
    timer = Timer.periodic(const Duration(seconds: 10), (Timer t) {
      ref
          .read(homeProvider.notifier)
          .getRouting(
            context: context,
            start: latLng,
            isOnline: (CourierStorage.getOnline()),
          );
    });
  }

  void getCurrentLocation() async {
    getSetProgressLocation();
    _geolocatorPlatform.getCurrentPosition().then((location) {
      currentLocation = location;
      latLng = LatLng(
        currentLocation?.latitude ?? latLng.latitude,
        currentLocation?.longitude ?? latLng.longitude,
      );
    });
    _geolocatorPlatform.getPositionStream().listen((newLoc) {
      currentLocation = newLoc;
      latLng = LatLng(
        currentLocation?.latitude ?? latLng.latitude,
        currentLocation?.longitude ?? latLng.longitude,
      );
      _delayed.run(() {
        CourierStorage.saveSelectedLocation(
          LatLng(
            currentLocation?.latitude ?? latLng.latitude,
            currentLocation?.longitude ?? latLng.longitude,
          ),
        );
      });
    });
  }

  Future<void> attachOrder(OrderDetailData? push) async {
    AppHelpers.showAlertDialog(
      context: context,
      child: PushOrder(pushModel: push ?? OrderDetailData(), isActive: false),
    );
    final ImageCropperForMarker image = ImageCropperForMarker();
    ref
        .read(homeProvider.notifier)
        .goMarket(
          context: context,
          orderId: push?.id,
          order: push,
          onSuccess: () async {
            ref
                .read(homeProvider.notifier)
                .getRoutingAll(
                  // ignore: use_build_context_synchronously
                  context: context,
                  start: LatLng(
                    LocalStorage.getAddressSelected()?.latitude ??
                        AppConstants.demoLatitude,
                    LocalStorage.getAddressSelected()?.longitude ??
                        AppConstants.demoLongitude,
                  ),
                  end: LatLng(
                    double.parse(push?.shop?.location?.latitude ?? "0"),
                    double.parse(push?.shop?.location?.longitude ?? "0"),
                  ),
                  market: Marker(
                    markerId: const MarkerId("Shop"),
                    position: LatLng(
                      double.parse(push?.shop?.location?.latitude ?? "0"),
                      double.parse(push?.shop?.location?.longitude ?? "0"),
                    ),
                    icon: await image.resizeAndCircle(
                      push?.shop?.logoImg ?? "",
                      120,
                    ),
                  ),
                );
          },
        );
  }

  Future<void> newOrder(OrderDetailData? push) async {
    AppHelpers.showAlertDialog(
      context: context,
      child: PushOrder(pushModel: push ?? OrderDetailData(), isActive: true),
    );
  }

  @override
  void initState() {
    checkPermission();
    setCustomMarkerIcon();
    getMyLocation();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // deliveryman settings fetch moved here from the retired host splash
      // (base_sdk's splash is courier-agnostic).
      ref.read(driverProvider.notifier).fetchDriverDetails(context: context);
      ref
          .read(courierProfileStatisticsProvider.notifier)
          .fetchProfileStatistics(context: context);
      ref
          .read(profileSettingsProvider.notifier)
          .fetchRequestResponse(context: context);
      ref.read(homeProvider.notifier).fetchCurrentOrder(context);
      ref.read(orderProvider.notifier).fetchActiveOrders(context);
    });
    if (CourierStorage.getOnline()) {
      Workmanager().registerPeriodicTask(
        "${DateTime.now().year}${DateTime.now().day}${DateTime.now().minute}${DateTime.now().second}",
        fetchBackground,
        frequency: const Duration(minutes: 10),
      );
      WidgetsBinding.instance.addPostFrameCallback((_) {
        getCurrentLocation();
      });
    }
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: isLtr ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        body: Consumer(
          builder: (context, ref, child) {
            final state = ref.watch(homeProvider);
            return Stack(
              children: [
                _map(context, ref),
                state.isGoRestaurant || state.isGoUser
                    ? state.parcelDetail == null
                          ? DeliverBottomSheetScreen(
                              order:
                                  push ??
                                  (state.orderDetail ?? OrderDetailData()),
                            )
                          : ParcelBottomSheetScreen(parcel: state.parcelDetail)
                    : BottomSheetScreen(isScrolling: state.isScrolling),
                state.isGoRestaurant || state.isGoUser
                    ? const SizedBox.shrink()
                    : _myFindButton(ref),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 400),
                  top: MediaQuery.paddingOf(context).top + 10.h,
                  left: state.isScrolling ? -64.w : 16.w,
                  child: ButtonsBouncingEffect(
                    child: GestureDetector(
                      onTap: () => context.pushRoute(const ProfileRoute()),
                      child: Hero(
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
                    ),
                  ),
                ),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 400),
                  top: MediaQuery.paddingOf(context).top + 80.h,
                  left: state.isScrolling ? -64.w : 12.w,
                  child: ButtonsBouncingEffect(
                    child: Consumer(
                      builder: (context, ref, child) {
                        ref.watch(profileImageProvider);
                        return Stack(
                          children: [
                            Container(
                              decoration: BoxDecoration(
                                color: AppStyle.primary,
                                borderRadius: BorderRadius.circular(16.r),
                              ),
                              margin: EdgeInsets.all(8.r),
                              child: IconButton(
                                onPressed: () =>
                                    context.pushRoute(const OrdersRoute()),
                                icon: const Icon(
                                  Remix.history_fill,
                                  color: AppStyle.white,
                                ),
                              ),
                            ),
                            Positioned(
                              top: 2.r,
                              right: 8.r,
                              child: Text(
                                ref
                                    .watch(orderProvider)
                                    .totalActiveOrder
                                    .toString(),
                                style: AppStyle.interBold(
                                  color: AppStyle.black,
                                  size: 18,
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 400),
                  top: MediaQuery.paddingOf(context).top + 150.h,
                  left: state.isScrolling ? -64.w : 12.w,
                  child: ButtonsBouncingEffect(
                    child: Container(
                      decoration: BoxDecoration(
                        color: AppStyle.primary,
                        borderRadius: BorderRadius.circular(16.r),
                      ),
                      margin: EdgeInsets.all(8.r),
                      child: IconButton(
                        onPressed: () =>
                            context.pushRoute(const DriverRouteRoute()),
                        icon: const Icon(
                          Remix.route_fill,
                          color: AppStyle.white,
                        ),
                      ),
                    ),
                  ),
                ),
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 400),
                  top: MediaQuery.paddingOf(context).top + 10.h,
                  right: state.isScrolling ? -120.w : 16.w,
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppStyle.white,
                      borderRadius: BorderRadius.circular(10.r),
                    ),
                    padding: EdgeInsets.all(6.r),
                    child: CustomToggle(
                      isOnline: (CourierStorage.getOnline()),
                      onChange: (bool value) {
                        if (value) {
                          Workmanager().registerPeriodicTask(
                            "${DateTime.now().year}${DateTime.now().day}${DateTime.now().minute}${DateTime.now().second}",
                            fetchBackground,
                            frequency: const Duration(minutes: 10),
                          );
                          getCurrentLocation();
                        } else {
                          timer?.cancel();
                          Workmanager().cancelAll();
                        }
                        ref
                            .read(homeProvider.notifier)
                            .setOnline(context: context);
                      },
                    ),
                  ),
                ),
                if (state.isLoading)
                  AnimatedPositioned(
                    duration: const Duration(milliseconds: 500),
                    child: _customLoading(context),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _map(BuildContext context, WidgetRef ref) {
    return SizedBox(
      width: MediaQuery.sizeOf(context).width,
      height: MediaQuery.sizeOf(context).height,
      child: GoogleMap(
        myLocationButtonEnabled: false,
        initialCameraPosition: CameraPosition(
          bearing: 0,
          target: LatLng(
            (LocalStorage.getAddressSelected()?.latitude ??
                AppConstants.demoLatitude),
            (LocalStorage.getAddressSelected()?.longitude ??
                AppConstants.demoLongitude),
          ),
          tilt: 0,
          zoom: 17,
        ),
        markers: {
          Marker(
            markerId: const MarkerId("source"),
            icon: myIcon,
            position: LatLng(
              currentLocation?.latitude ?? latLng.latitude,
              currentLocation?.longitude ?? latLng.longitude,
            ),
          ),
          ...ref.watch(homeProvider).markers,
        },
        polygons: ref.watch(homeProvider).polygon,
        polylines:
            ref.watch(homeProvider).isGoRestaurant ||
                ref.watch(homeProvider).isGoUser
            ? {
                Polyline(
                  polylineId: const PolylineId("startLocation"),
                  points: ref.watch(homeProvider).endPolylineCoordinates,
                  color: AppStyle.primary.withOpacity(0.4),
                  width: 6,
                ),
                Polyline(
                  polylineId: const PolylineId("market"),
                  points: ref.watch(homeProvider).polylineCoordinates,
                  color: AppStyle.primary,
                  width: 6,
                ),
              }
            : {},
        mapToolbarEnabled: true,
        zoomControlsEnabled: false,
        onMapCreated: (controller) {
          googleMapController = controller;
        },
        onCameraMoveStarted: () {
          if (!(LocalStorage.getUser()?.active ?? false)) {
            ref.read(homeProvider.notifier).scrolling(true);
          }
        },
        onCameraIdle: () {
          _delayed.run(() {
            ref.read(homeProvider.notifier).scrolling(false);
          });
        },
        padding: EdgeInsets.only(
          bottom: ref.watch(homeProvider).isGoRestaurant
              ? 90.h
              : ref.watch(homeProvider).isScrolling
              ? 60.h
              : 330.h,
        ),
      ),
    );
  }

  Widget _customLoading(BuildContext context) {
    return BlurWrap(
      radius: BorderRadius.zero,
      blur: 1,
      child: Container(
        width: MediaQuery.sizeOf(context).width,
        height: MediaQuery.sizeOf(context).height,
        color: AppStyle.white.withOpacity(0.3),
        child: const Loading(),
      ),
    );
  }

  Widget _myFindButton(WidgetRef ref) {
    return AnimatedPositioned(
      bottom: 342.h,
      right: ref.watch(homeProvider).isScrolling ? -64.w : 16.w,
      duration: const Duration(milliseconds: 400),
      child: GestureDetector(
        onTap: () async => await getMyLocation(),
        child: Container(
          width: 50.r,
          height: 50.r,
          decoration: BoxDecoration(
            color: AppStyle.white,
            borderRadius: BorderRadius.circular(10.r),
            boxShadow: const [
              BoxShadow(
                color: Color(0xFF7D7D7D),
                blurRadius: 2,
                offset: Offset(0, 2),
              ),
            ],
          ),
          child: const Icon(Remix.focus_3_fill),
        ),
      ),
    );
  }
}
