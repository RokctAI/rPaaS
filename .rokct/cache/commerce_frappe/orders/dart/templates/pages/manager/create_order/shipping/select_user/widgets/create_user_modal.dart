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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';
import 'package:base_sdk/src/presentation/components/text_fields/underlined_text_field.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/app_validators.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/user/create/create_user_provider.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/user/order_user_provider.dart';

class CreateUserModal extends StatefulWidget {
  const CreateUserModal({super.key}) ;

  @override
  State<CreateUserModal> createState() => _CreateUserModalState();
}

class _CreateUserModalState extends State<CreateUserModal> {
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: Padding(
        padding: REdgeInsets.symmetric(horizontal: 16),
        child: Consumer(
          builder: (context, ref, child) {
            final event = ref.read(createUserProvider.notifier);
            final state = ref.watch(createUserProvider);
            return Form(
              key: _formKey,
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const ModalDrag(),
                    TitleAndIcon(
                      title: AppHelpers.getTranslation(TrKeys.addUser),
                    ),
                    24.verticalSpace,
                    UnderlinedTextField(
                      label: '${AppHelpers.getTranslation(TrKeys.firstname)}*',
                      inputType: TextInputType.text,
                      textCapitalization: TextCapitalization.sentences,
                      textInputAction: TextInputAction.next,
                      onChanged: event.setFirstname,
                      validator: AppValidators.isNotEmptyValidator,
                    ),
                    24.verticalSpace,
                    UnderlinedTextField(
                      label: '${AppHelpers.getTranslation(TrKeys.lastname)}*',
                      inputType: TextInputType.text,
                      textCapitalization: TextCapitalization.sentences,
                      textInputAction: TextInputAction.next,
                      onChanged: event.setLastname,
                      validator: AppValidators.isNotEmptyValidator,
                    ),
                    24.verticalSpace,
                    UnderlinedTextField(
                      label: '${AppHelpers.getTranslation(TrKeys.phoneNumber)}*',
                      inputType: TextInputType.phone,
                      textInputAction: TextInputAction.next,
                      onChanged: event.setPhone,
                      validator: AppValidators.isNotEmptyValidator,
                    ),
                    24.verticalSpace,
                    UnderlinedTextField(
                      label: '${AppHelpers.getTranslation(TrKeys.email)}*',
                      inputType: TextInputType.emailAddress,
                      textCapitalization: TextCapitalization.none,
                      textInputAction: TextInputAction.done,
                      onChanged: event.setEmail,
                      validator: AppValidators.isNotEmptyValidator,
                    ),
                    24.verticalSpace,
                    CustomButton(
                      title: AppHelpers.getTranslation(TrKeys.save),
                      isLoading: state.isLoading,
                      onPressed: () {
                        if (_formKey.currentState?.validate() ?? false) {
                          event.createUser(
                            context,
                            created: (user) {
                              context.maybePop();
                              ref
                                  .read(orderUserProvider.notifier)
                                  .addCreatedUser(user);
                            },
                            failed: () => AppHelpers.showCheckTopSnackBar(
                              context,
                              AppHelpers.getTranslation(TrKeys.failed),
                            ),
                          );
                        }
                      },
                    ),
                    24.verticalSpace,
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
