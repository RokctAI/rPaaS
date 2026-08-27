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

import 'package:flutter/cupertino.dart';
import 'package:auto_route/auto_route.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/title_icon.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_wrap.dart';
import 'package:base_sdk/src/presentation/components/helper/modal_drag.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';

class SelectDateModal extends StatefulWidget {
  final String? initialDate;
  final Function(DateTime? date) onDateSaved;

  const SelectDateModal(
      {super.key, this.initialDate, required this.onDateSaved});

  @override
  State<SelectDateModal> createState() => _SelectDateModalState();
}

class _SelectDateModalState extends State<SelectDateModal> {
  DateTime? _date;

  @override
  void initState() {
    if (widget.initialDate != null || widget.initialDate!.isEmpty) {
      _date = DateTime.tryParse(widget.initialDate!)?.toLocal();
    } else {
      _date = DateTime.now();
    }
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return ModalWrap(
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          const ModalDrag(),
          Padding(
            padding: REdgeInsets.symmetric(horizontal: 16),
            child: TitleAndIcon(
              title: AppHelpers.getTranslation(TrKeys.deliveryTime),
            ),
          ),
          Padding(
            padding: REdgeInsets.symmetric(horizontal: 16),
            child: Text(
              AppHelpers.getTranslation(TrKeys.selectDeliveryDate),
              style: AppStyle.interNormal(
                size: 14.sp,
                color: AppStyle.blackColor,
                letterSpacing: -0.3,
              ),
            ),
          ),
          SizedBox(
            height: 300.r,
            child: CupertinoTheme(
              data: const CupertinoThemeData(
                brightness: Brightness.light,
              ),
              child: CupertinoDatePicker(
                mode: CupertinoDatePickerMode.date,
                initialDateTime: _date,
                minimumDate: _date,
                onDateTimeChanged: (DateTime value) {
                  _date = value;
                },
              ),
            ),
          ),
          16.verticalSpace,
          Padding(
            padding: REdgeInsets.symmetric(horizontal: 16),
            child: CustomButton(
              title: AppHelpers.getTranslation(TrKeys.save),
              onPressed: () {
                widget.onDateSaved(_date);
                context.maybePop();
              },
            ),
          ),
          12.verticalSpace,
        ],
      ),
    );
  }
}
