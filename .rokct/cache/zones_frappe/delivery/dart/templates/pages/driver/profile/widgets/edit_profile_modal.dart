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
import 'package:flutter/services.dart';
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl_phone_field/intl_phone_field.dart';
import 'package:intl_phone_field/phone_number.dart';

import 'package:base_sdk/src/presentation/components/loading.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:${package}/presentation/pages/profile/edit_car.dart';
import 'package:${package}/presentation/component/helper/keyboard_disable.dart';
import 'package:${package}/presentation/component/shop_avarat.dart';
import 'package:${package}/presentation/component/text_fields/underline_bordered_text_field.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/local_storage.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_edit_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_image_provider.dart';
import 'package:delivery_sdk/src/driver/application/profile/provider/profile_settings_provider.dart';
import 'package:delivery_sdk/src/driver/infrastructure/services/courier_constants.dart';

class EditProfileModal extends ConsumerStatefulWidget {
  const EditProfileModal({super.key});

  @override
  ConsumerState<EditProfileModal> createState() => _EditProfileModalState();
}

class _EditProfileModalState extends ConsumerState<EditProfileModal> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(profileSettingsProvider.notifier)
          .fetchProfileDetails(
            context: context,
            checkYourNetwork: () {
              AppHelpers.showCheckTopSnackBar(
                context,
                AppHelpers.getTranslation(TrKeys.checkYourNetworkConnection),
              );
            },
            setImage: (url) {
              ref.read(profileImageProvider.notifier).setUrl(url);
            },
            setUserData: (user) {
              ref.read(profileEditProvider.notifier).setInitialInfo(user);
            },
          );
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileSettingsProvider);
    return state.isLoading || state.userData == null
        ? Padding(
            padding: REdgeInsets.symmetric(vertical: 30),
            child: const Loading(),
          )
        : KeyboardDisable(
            child: Consumer(
              builder: (context, ref, child) {
                final editState = ref.watch(profileEditProvider);
                final editNotifier = ref.read(profileEditProvider.notifier);
                return ListView(
                  physics: const BouncingScrollPhysics(),
                  padding: EdgeInsets.zero,
                  shrinkWrap: true,
                  children: [
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16.w),
                      child: Column(
                        children: [
                          TitleAndIcon(
                            title: AppHelpers.getTranslation(
                              TrKeys.profileSettings,
                            ),
                          ),
                          24.verticalSpace,
                          Row(
                            children: [
                              Consumer(
                                builder: (context, ref, child) {
                                  final imageState = ref.watch(
                                    profileImageProvider,
                                  );
                                  return Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      ShopAvatar(
                                        radius: 16,
                                        imageUrl: imageState.imageUrl,
                                        path: imageState.path,
                                        size: 50,
                                        padding: 6,
                                        bgColor: AppStyle.black.withOpacity(
                                          0.27,
                                        ),
                                      ),
                                      Container(
                                        width: 50.r,
                                        height: 50.r,
                                        decoration: BoxDecoration(
                                          borderRadius: BorderRadius.circular(
                                            16.r,
                                          ),
                                          color: AppStyle.black.withOpacity(
                                            0.27,
                                          ),
                                        ),
                                      ),
                                      IconButton(
                                        icon: Icon(
                                          Remix.camera_fill,
                                          color: AppStyle.white,
                                          size: 20.r,
                                        ),
                                        onPressed: () async {
                                          final XFile? pickedFile =
                                              await ImagePicker().pickImage(
                                                source: ImageSource.gallery,
                                                maxWidth: 1000,
                                                maxHeight: 1000,
                                                imageQuality: 90,
                                              );
                                          if (pickedFile != null) {
                                            // ignore: use_build_context_synchronously
                                            ref
                                                .read(
                                                  profileImageProvider.notifier,
                                                )
                                                .changePhoto(
                                                  // ignore: use_build_context_synchronously
                                                  context: context,
                                                  path: pickedFile.path,
                                                  firstname:
                                                      state.userData?.firstname,
                                                );
                                          }
                                        },
                                      ),
                                    ],
                                  );
                                },
                              ),
                              16.horizontalSpace,
                              Expanded(
                                child: UnderlinedBorderTextField(
                                  label: AppHelpers.getTranslation(
                                    TrKeys.firstname,
                                  ),
                                  initialText: editState.firstname,
                                  onChanged: editNotifier.setFirstname,
                                  descriptionText: editState.isFirstnameError
                                      ? AppHelpers.getTranslation(
                                          TrKeys.firstnameCannotBeEmpty,
                                        )
                                      : null,
                                  isError: editState.isFirstnameError,
                                ),
                              ),
                            ],
                          ),
                          24.verticalSpace,
                          UnderlinedBorderTextField(
                            label: AppHelpers.getTranslation(TrKeys.lastname),
                            initialText: editState.lastname,
                            onChanged: editNotifier.setLastname,
                            descriptionText: editState.isLastnameError
                                ? AppHelpers.getTranslation(
                                    TrKeys.lastnameCannotBeEmpty,
                                  )
                                : null,
                            isError: editState.isLastnameError,
                          ),
                          24.verticalSpace,
                          if (!CourierConstants.isSpecificNumberEnabled)
                            UnderlinedBorderTextField(
                              label: AppHelpers.getTranslation(
                                TrKeys.phoneNumber,
                              ),
                              initialText: editState.phone,
                              inputType: TextInputType.phone,
                              readOnly: !editState.isPhoneEditable,
                              onChanged: editNotifier.setPhone,
                            ),
                          if (CourierConstants.isSpecificNumberEnabled)
                            Directionality(
                              textDirection: TextDirection.ltr,
                              child: IntlPhoneField(
                                showCountryFlag: AppConstants.showFlag,
                                showDropdownIcon: AppConstants.showArrowIcon,
                                disableLengthCheck:
                                    !AppConstants.isNumberLengthAlwaysSame,
                                onChanged: (phoneNum) => editNotifier.setPhone(
                                  phoneNum.completeNumber,
                                ),
                                validator: (s) {
                                  if (AppConstants.isNumberLengthAlwaysSame &&
                                      (s?.isValidNumber() ?? false)) {
                                    return AppHelpers.getTranslation(
                                      TrKeys.phoneNumberIsNotValid,
                                    );
                                  }
                                  return null;
                                },
                                keyboardType: TextInputType.number,
                                autovalidateMode: AutovalidateMode.disabled,
                                initialCountryCode: PhoneNumber.fromCompleteNumber(
                                  completeNumber:
                                      "+${editState.phone.replaceAll('+', "")}",
                                ).countryISOCode,
                                initialValue: PhoneNumber.fromCompleteNumber(
                                  completeNumber:
                                      "+${editState.phone.replaceAll('+', "")}",
                                ).number,
                                enabled: editState.isPhoneEditable,
                                invalidNumberMessage: AppHelpers.getTranslation(
                                  TrKeys.phoneNumberIsNotValid,
                                ),
                                inputFormatters: [
                                  FilteringTextInputFormatter.digitsOnly,
                                ],
                                textAlignVertical: TextAlignVertical.center,
                                decoration: InputDecoration(
                                  counterText: '',
                                  enabledBorder: UnderlineInputBorder(
                                    borderSide: BorderSide.merge(
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                    ),
                                  ),
                                  errorBorder: UnderlineInputBorder(
                                    borderSide: BorderSide.merge(
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                    ),
                                  ),
                                  border: const UnderlineInputBorder(),
                                  focusedErrorBorder:
                                      const UnderlineInputBorder(),
                                  disabledBorder: UnderlineInputBorder(
                                    borderSide: BorderSide.merge(
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                      const BorderSide(
                                        color: AppStyle.borderColor,
                                      ),
                                    ),
                                  ),
                                  focusedBorder: const UnderlineInputBorder(),
                                ),
                              ),
                            ),
                          24.verticalSpace,
                          UnderlinedBorderTextField(
                            label: AppHelpers.getTranslation(TrKeys.email),
                            initialText: editState.email,
                            inputType: TextInputType.emailAddress,
                            readOnly: !editState.isEmailEditable,
                            onChanged: editNotifier.setEmail,
                          ),
                          24.verticalSpace,
                          UnderlinedBorderTextField(
                            label: AppHelpers.getTranslation(TrKeys.password),
                            obscure: editState.showPassword,
                            onChanged: editNotifier.setPassword,
                            isError: editState.isPasswordError,
                            descriptionText: editState.isPasswordError
                                ? AppHelpers.getTranslation(
                                    TrKeys
                                        .passwordShouldContainMinimum6Characters,
                                  )
                                : null,
                            suffixIcon: IconButton(
                              splashRadius: 25,
                              icon: Icon(
                                editState.showPassword
                                    ? Remix.eye_line
                                    : Remix.eye_close_line,
                                color: AppStyle.black,
                                size: 20.r,
                              ),
                              onPressed: editNotifier.toggleShowPassword,
                            ),
                          ),
                          24.verticalSpace,
                          UnderlinedBorderTextField(
                            label: AppHelpers.getTranslation(
                              TrKeys.confirmPassword,
                            ),
                            obscure: editState.showConfirmPassword,
                            onChanged: editNotifier.setConfirmPassword,
                            isError: editState.isConfirmPasswordError,
                            descriptionText: editState.isConfirmPasswordError
                                ? AppHelpers.getTranslation(
                                    TrKeys
                                        .confirmPasswordDoesntMatchWithNewPassword,
                                  )
                                : null,
                            suffixIcon: IconButton(
                              splashRadius: 25.r,
                              icon: Icon(
                                editState.showConfirmPassword
                                    ? Remix.eye_line
                                    : Remix.eye_close_line,
                                color: AppStyle.black,
                                size: 20.r,
                              ),
                              onPressed: editNotifier.toggleShowConfirmPassword,
                            ),
                          ),
                        ],
                      ),
                    ),
                    24.verticalSpace,
                    const Divider(),
                    GestureDetector(
                      onTap: () {
                        AppHelpers.showCustomModalBottomSheet(
                          paddingTop: 120.h,
                          context: context,
                          modal: const EditCar(),
                          isDarkMode: false,
                        );
                      },
                      child: Container(
                        color: AppStyle.transparent,
                        child: Padding(
                          padding: EdgeInsets.all(16.r),
                          child: Row(
                            children: [
                              Icon(Remix.time_fill, size: 20.r),
                              8.horizontalSpace,
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    AppHelpers.getTranslation(
                                      TrKeys.deliveryVehicle,
                                    ),
                                    style: AppStyle.interNormal(
                                      size: 12.sp,
                                      color: AppStyle.black,
                                    ),
                                  ),
                                  Text(
                                    "${LocalStorage.getDeliveryInfo()?.data?.number ?? ''} — ${LocalStorage.getDeliveryInfo()?.data?.model ?? ''}, ${LocalStorage.getDeliveryInfo()?.data?.color ?? ''}",
                                    style: AppStyle.interNormal(
                                      size: 12.sp,
                                      color: AppStyle.black,
                                    ),
                                  ),
                                ],
                              ),
                              const Spacer(),
                              const Icon(Remix.arrow_right_s_line),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const Divider(),
                    Padding(
                      padding: EdgeInsets.all(16.r),
                      child: CustomButton(
                        title: AppHelpers.getTranslation(TrKeys.save),
                        isLoading: editState.isLoading,
                        onPressed: () {
                          editNotifier.updateGeneralInfo(
                            context: context,
                            checkYourNetwork: () {
                              AppHelpers.showCheckTopSnackBar(
                                context,
                                AppHelpers.getTranslation(
                                  TrKeys.checkYourNetworkConnection,
                                ),
                              );
                            },
                            updated: context.router.maybePop,
                          );
                        },
                      ),
                    ),
                  ],
                );
              },
            ),
          );
  }
}
