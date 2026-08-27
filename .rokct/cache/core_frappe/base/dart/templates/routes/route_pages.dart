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


// Host-side route shells for base_sdk's initial pages.
//
// auto_route's generator only scans the host package, so SDK-resident pages
// are wrapped in thin @RoutePage shells here. Feature SDKs contribute their
// own shells through their manifest installs when they own routed pages.
import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';

import 'package:base_sdk/src/presentation/pages/initial/maintenance/maintenance_page.dart' as pages;
import 'package:base_sdk/src/presentation/pages/initial/no_connection/no_connection_page.dart' as pages;
import 'package:base_sdk/src/presentation/pages/initial/splash/splash_page.dart' as pages;
import 'package:base_sdk/src/presentation/pages/initial/ui_type/ui_type_page.dart' as pages;
import 'package:base_sdk/src/presentation/pages/profile/generic_profile_page.dart' as pages;

/// Host route shell for [pages.SplashPage] (base_sdk-resident page).
@RoutePage(name: 'SplashRoute')
class SplashRouteView extends StatelessWidget {
  const SplashRouteView({super.key});

  @override
  Widget build(BuildContext context) => const pages.SplashPage();
}

/// Host route shell for [pages.NoConnectionPage] (base_sdk-resident page).
@RoutePage(name: 'NoConnectionRoute')
class NoConnectionRouteView extends StatelessWidget {
  const NoConnectionRouteView({super.key});

  @override
  Widget build(BuildContext context) => const pages.NoConnectionPage();
}

/// Host route shell for [pages.MaintenancePage] (base_sdk-resident page).
@RoutePage(name: 'MaintenanceRoute')
class MaintenanceRouteView extends StatelessWidget {
  const MaintenanceRouteView({super.key});

  @override
  Widget build(BuildContext context) => const pages.MaintenancePage();
}

/// Host route shell for [pages.GenericProfilePage] (base_sdk-resident page).
/// Named GenericProfileRoute: marketplace_sdk already owns ProfileRoute.
@RoutePage(name: 'GenericProfileRoute')
class GenericProfileRouteView extends StatelessWidget {
  const GenericProfileRouteView({super.key});

  @override
  Widget build(BuildContext context) => const pages.GenericProfilePage();
}

/// Host route shell for [pages.UiTypePage] (base_sdk-resident page).
@RoutePage(name: 'UiTypeRoute')
class UiTypeRouteView extends StatelessWidget {
  final bool isBack;
  const UiTypeRouteView({super.key, this.isBack = false});

  @override
  Widget build(BuildContext context) => pages.UiTypePage(isBack: isBack);
}
