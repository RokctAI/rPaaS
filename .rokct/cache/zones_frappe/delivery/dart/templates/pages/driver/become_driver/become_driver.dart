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

// Host composition file (auth_sdk's auth_route_pages.dart precedent).
// delivery_sdk's ported BecomeDriverPage lives in the SDK's lib/src/, and
// auto_route's codegen only generates route classes for @RoutePage widgets
// in the HOST's own lib/ — so this thin wrapper is what actually gets the
// BecomeDriverRoute class generated.
//
// It installs to lib/presentation/pages/auth/become_driver/become_driver.dart
// — the exact path the host's tracked app_router.dart imports today. While
// paas_driver still tracks its own copy there the installer's hash guard
// skips this file; the SDK copy takes over when the host copy is deleted
// (M3, the auth flip — the same commit that retires the legacy in-page
// vehicle form, whose capture now runs as this SDK's `registration_steps`
// vehicle-details slide).

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';

import 'package:delivery_sdk/src/common/presentation/pages/become_driver/become_driver.dart'
    as delivery;

@RoutePage(name: 'BecomeDriverRoute')
class BecomeDriverRouteView extends StatelessWidget {
  const BecomeDriverRouteView({super.key});

  @override
  Widget build(BuildContext context) => const delivery.BecomeDriverPage();
}
