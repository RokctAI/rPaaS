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


// Host-shell theme shim: composed-app pages import
// package:<app>/presentation/theme/theme.dart; the real theme lives in
// base_sdk. Re-exported here so installed template pages resolve unchanged.
//
// This installed file is also where THE APP'S brand palette lives: the
// kernel ships neutral defaults only, and [applyAppBrandColors] (call it in
// main() before runApp) injects this app's values via
// AppStyle.injectBrandColors. Customize the values here — the installer
// never overwrites an edited copy.
import 'package:base_sdk/src/presentation/theme/app_style.dart';

export 'package:base_sdk/src/presentation/theme/app_style.dart';
export 'package:base_sdk/src/presentation/theme/map_themes.dart';

/// Injects this app's brand palette into the shared AppStyle tokens.
/// Default template: keeps the kernel's neutral defaults — replace with
/// your app's palette on install.
void applyAppBrandColors() {
  AppStyle.injectBrandColors();
}
