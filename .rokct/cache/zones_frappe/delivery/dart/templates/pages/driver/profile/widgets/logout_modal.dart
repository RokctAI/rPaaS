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

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_sign_in/google_sign_in.dart';



import 'package:${package}/presentation/routes/app_router.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_settings_provider.dart';

class LogoutModal extends StatelessWidget {
  final bool isDeleteAccount;

  const LogoutModal({super.key, this.isDeleteAccount = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: REdgeInsets.symmetric(horizontal: 15),
      child: Column(
        children: [
          Text(
            AppHelpers.getTranslation(isDeleteAccount
                ? TrKeys.areYouSure
                : TrKeys.doYouReallyWantToLogout),
            style: AppStyle.interSemi(size: 16.sp),
            textAlign: TextAlign.center,
          ),
          40.verticalSpace,
          Row(
            children: [
              Expanded(
                child: CustomButton(
                    borderColor: AppStyle.black,
                    background: AppStyle.transparent,
                    title: AppHelpers.getTranslation(TrKeys.cancel),
                    onPressed: () {
                      Navigator.pop(context);
                    }),
              ),
              16.horizontalSpace,
              Expanded(
                child: Consumer(builder: (context, ref, child) {
                  if (isDeleteAccount) {
                    return CustomButton(
                        background: AppStyle.red,
                        textColor: AppStyle.white,
                        title: AppHelpers.getTranslation(TrKeys.deleteAccount),
                        onPressed: () {
                          ref
                              .read(profileSettingsProvider.notifier)
                              .deleteAccount(context);
                        });
                  } else {
                    return CustomButton(
                        title: AppHelpers.getTranslation(TrKeys.logout),
                        onPressed: () {
                          final GoogleSignIn signIn = GoogleSignIn();
                          signIn.disconnect();
                          signIn.signOut();
                          LocalStorage.logout();
                          context.router.popUntilRoot();
                          context.replaceRoute(const LoginRoute());
                        });
                  }
                }),
              ),
            ],
          ),
          24.verticalSpace,
        ],
      ),
    );
  }
}
