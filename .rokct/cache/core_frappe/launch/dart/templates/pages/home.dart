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
import 'package:remixicon/remixicon.dart';
import 'package:launch_sdk/launch_sdk.dart';
import 'package:users_sdk/users_sdk.dart';
import 'package:auto_route/auto_route.dart';
import 'widgets/app_item.dart';
// @launcher-glance-imports
import 'package:base_sdk/base_sdk.dart';
import 'package:base_sdk/src/application/app_widget/app_provider.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/components/text_fields/search_text_field.dart';
import 'package:get_it/get_it.dart';
// @launcher-user-avatar-imports

@RoutePage(name: 'LauncherHomeRoute')
class LauncherHomePage extends ConsumerWidget {
  const LauncherHomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(appProvider);
    final state = ref.watch(launchProvider);
    final notifier = ref.read(launchProvider.notifier);
    final searchController = TextEditingController();

    final isDark = appState.isDarkMode;
    // `users_sdk` currently has no profile/session-state provider to back
    // the @launcher-user-avatar marker below (it was already dead code —
    // computed but never rendered, since that marker has always been
    // empty). Out of scope for this pass: filling it needs a real users_sdk
    // API for "is a user logged in," which doesn't exist yet.

    return Scaffold(
      backgroundColor: isDark ? AppStyle.blackColor : AppStyle.white,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  // @launcher-user-avatar
                  const SizedBox(width: 12),
                  GestureDetector(
                    onTap: () =>
                        ref.read(appProvider.notifier).changeTheme(!isDark),
                    child: Icon(
                      isDark ? RemixIcons.sun_line : RemixIcons.moon_line,
                      color: isDark ? AppStyle.white : AppStyle.blackColor,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SearchTextField(
                      textEditingController: searchController,
                      onChanged: (value) => notifier.filterApps(value),
                      hintText: 'Search apps...',
                      bgColor: AppStyle.bgGrey,
                    ),
                  ),
                ],
              ),
            ),
            // @launcher-glance
            //
            // Generic and host-agnostic by construction: launch_sdk has no
            // urgent signal of its own (an installed-apps list carries no
            // notion of "urgent"), and per ADR-005 must not import
            // comms_sdk/productivity_sdk/etc. directly to invent one. Any
            // app composing launch_sdk that wants glance content registers
            // a LaunchGlanceSource with GetIt (see launch_glance_source.dart
            // for the seam); apps that don't just render nothing here,
            // identical to the "nothing urgent right now" case.
            GlanceCard(
              items: (GetIt.instance.isRegistered<LaunchGlanceSource>()
                      ? GetIt.instance.get<LaunchGlanceSource>().build()
                      : const <LaunchGlanceSignal>[])
                  .map((signal) => GlanceCardItem(
                        icon: signal.icon,
                        text: signal.text,
                        onTap: signal.onTap,
                      ))
                  .toList(),
            ),
            Expanded(
              child: state.isLoading
                  ? Loading(
                      bgColor: isDark ? AppStyle.white : AppStyle.blackColor)
                  // An enumeration failure and a genuinely empty device both
                  // produce an empty list. Say which, so a broken launcher
                  // doesn't read as a bare one.
                  : state.error != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 32),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  "Couldn't load your apps",
                                  style: TextStyle(color: AppStyle.text),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  state.error!,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: AppStyle.text, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        )
                  : state.filteredApps.isEmpty
                      ? const Center(
                          child: Text(
                            'No apps found',
                            style: TextStyle(color: AppStyle.text),
                          ),
                        )
                      : ListView.builder(
                          itemCount: state.filteredApps.length,
                          itemBuilder: (context, index) {
                            final app = state.filteredApps[index];
                            return LauncherAppItem(
                              app: app,
                              onTap: () => notifier.startApp(app.packageName),
                              onLongPress: () =>
                                  notifier.openAppSettings(app.packageName),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
