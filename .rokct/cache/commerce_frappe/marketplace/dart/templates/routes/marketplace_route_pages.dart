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


// ignore_for_file: unused_result

// Host-side route shell + profile-host wiring for marketplace_sdk.
//
// auto_route's generator only scans the host package, so the SDK-resident
// profile host is wrapped in a thin @RoutePage shell here (the same pattern
// as base_sdk's route_pages.dart and lms_sdk's lms_route_pages.dart).
import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/application/profile/profile_provider.dart';
import 'package:base_sdk/src/application/shop_order/shop_order_provider.dart';
import 'package:base_sdk/src/navigation/app_routes.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/pages/profile/generic_profile_page.dart'
    as pages;
import 'package:base_sdk/src/presentation/pages/profile/profile_section_registry.dart';
import 'package:marketplace_sdk/src/common/presentation/pages/profile/marketplace_profile_sections.dart';
import 'package:marketplace_sdk/src/common/presentation/pages/profile/widgets/my_account.dart';

/// Registers every marketplace profile section with base_sdk's
/// [ProfileSectionRegistry] — called once at boot from this SDK's
/// `di_hooks` manifest entry. Everything routes through base_sdk seams
/// (AppRoutes / EmbeddedWidgets), so no generated route class is needed
/// here beyond the shell below.
void registerMarketplaceProfileSections() {
  // Header settings affordance — the old app-bar gear icon, mapped onto the
  // host's edit-profile slot: MyAccount is the settings hub that carries
  // Edit account (plus password/addresses/notifications/language/currency).
  ProfileSectionRegistry.I.onEditProfile = (context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const MyAccount(isBackButton: false),
      ),
    );
  };

  // Header logout affordance — the confirmed branch of the old page's
  // DeleteScreen dialog, verbatim; the host page already ran its own
  // logout confirmation, so no second dialog.
  ProfileSectionRegistry.I.onLogout = (context) {
    MarketplaceProfileHeaderActions.cancelNotificationTimer();
    final container = ProviderScope.containerOf(context, listen: false);
    container.read(profileProvider.notifier).logOut();
    container.refresh(shopOrderProvider);
    container.refresh(profileProvider);
    context.router.popUntilRoot();
    AppRoutes.I.replaceLoginRoute(context);
  };

  MarketplaceProfileSections.register();
}

/// Host route shell for the customer profile, now rendering base_sdk's
/// generic profile host. Route name (ProfileRoute) and constructor params
/// match the deprecated marketplace ProfilePage, so existing navigation
/// call-sites keep working; the sections come from
/// [registerMarketplaceProfileSections].
@RoutePage(name: 'ProfileRoute')
class ProfileRouteView extends StatelessWidget {
  final bool isBackButton;
  final Function()? onCardAdded;

  const ProfileRouteView({
    super.key,
    this.onCardAdded,
    this.isBackButton = true,
  });

  @override
  Widget build(BuildContext context) {
    // Sections are registered at boot; the per-navigation card-added
    // callback rides this slot instead of a constructor param.
    MarketplaceProfileSections.onCardAdded = onCardAdded;
    return Stack(
      children: [
        const pages.GenericProfilePage(),
        // The old page's floating back button (FAB startFloat + 16.w pad).
        if (isBackButton)
          Positioned(
            left: 32.w,
            bottom: 16.h,
            child: const SafeArea(child: PopButton()),
          ),
      ],
    );
  }
}
