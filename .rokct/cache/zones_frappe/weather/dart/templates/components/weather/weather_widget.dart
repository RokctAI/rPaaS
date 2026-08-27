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

import 'package:weather_sdk/weather_sdk.dart';

/// Host-side weather wiring, installed by weather_sdk's manifest to
/// `lib/presentation/components/weather/weather_widget.dart`.
///
/// Two jobs:
/// 1. [configureWeatherSdk] - one-time startup hook that tells the SDK where
///    the shop is. The default below reads nothing host-specific (so a fresh
///    compose builds green and falls back to the DEMO_LATITUDE/-LONGITUDE
///    dart-defines); a POS/manager host edits it to return the logged-in
///    shop's stored coordinates (pos main read them from its
///    LocalStorage.getShopLocation()). The installer's hash guard treats
///    that edit as host-owned and will not clobber it on recompose.
/// 2. [AppWeatherWidget] - the widget shells embed (header slot or via
///    EmbeddedWidgets.I.weatherHeaderWidget()). Adaptive per Ray: full
///    interactive dialog experience on large screens, minimal popup-free
///    inline summary on small screens.
bool _configured = false;

void configureWeatherSdk() {
  if (_configured) return;
  _configured = true;

  WeatherSdkConfig.locationResolver = () {
    // HOST HOOK: return the shop/branch coordinates, e.g.
    //
    //   final shop = LocalStorage.getShopData();
    //   if (shop?.latitude != null && shop?.longitude != null) {
    //     return WeatherLocation(
    //       latitude: shop!.latitude!,
    //       longitude: shop.longitude!,
    //     );
    //   }
    //
    // Returning null falls back to the DEMO_LATITUDE/DEMO_LONGITUDE
    // dart-defines.
    return null;
  };

  // The OpenWeatherMap key (extended day-4-6 forecast only) defaults to the
  // OPEN_WEATHER_API_KEY dart-define. If this host hydrates remote config at
  // startup (pos main's get_remote_config pattern), assign it there instead:
  //
  //   WeatherSdkConfig.openWeatherApiKey = remote.getString('openWeatherApiKey');
  //   WeatherSdkConfig.rainPop = remote.getInt('rainPOP');
  //   WeatherSdkConfig.useNetworkIcons = remote.getBool('weatherIcon');
  //   WeatherSdkConfig.refreshInterval =
  //       Duration(minutes: remote.getInt('weatherRefresher'));
}

/// Embeddable adaptive weather widget for this app's shell.
class AppWeatherWidget extends StatelessWidget {
  /// See [WeatherWidget.inlineExpansion]: pass false when embedding in a
  /// fixed-height header and place [WeatherInlineForecast] in the body
  /// instead.
  final bool inlineExpansion;

  const AppWeatherWidget({super.key, this.inlineExpansion = true});

  @override
  Widget build(BuildContext context) {
    configureWeatherSdk();
    return WeatherWidget(inlineExpansion: inlineExpansion);
  }
}
