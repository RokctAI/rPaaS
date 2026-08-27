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
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'widgets/main_group_item.dart';
import 'details/extras_group_details_modal.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/helper/no_data_info.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:products_sdk/src/manager/application/extras/extras_provider.dart';

class ExtrasBody extends StatelessWidget {
  final RefreshController refreshController;

  const ExtrasBody({super.key, required this.refreshController});

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, child) {
        final state = ref.watch(extrasProvider);
        final event = ref.read(extrasProvider.notifier);
        return SmartRefresher(
          physics: const NeverScrollableScrollPhysics(),
          controller: refreshController,
          onRefresh: () =>
              event.fetchGroups(refreshController: refreshController),
          child: state.isLoading
              ? Center(
                  child: SizedBox(
                    width: 30.r,
                    height: 30.r,
                    child: CircularProgressIndicator(
                      strokeWidth: 4.r,
                      color: AppStyle.blackColor,
                    ),
                  ),
                )
              : state.groups.isEmpty
                  ? NoDataInfo(title: AppHelpers.getTranslation(TrKeys.noData))
                  : ListView.builder(
                      physics: const NeverScrollableScrollPhysics(),
                      shrinkWrap: true,
                      itemCount: state.groups.length,
                      padding: REdgeInsets.only(
                          right: 16, top: 20, left: 16, bottom: 100),
                      itemBuilder: (context, index) => MainGroupItem(
                        group: state.groups[index],
                        onTap: () => AppHelpers.showCustomModalBottomSheet(
                          context: context,
                          modal: ExtrasGroupDetailsModal(
                            group: state.groups[index],
                          ),
                          isDarkMode: true,
                        ),
                      ),
                    ),
        );
      },
    );
  }
}
