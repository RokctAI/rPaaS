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

import 'widgets/addon_item.dart';
import 'edit/edit_addon_modal.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:products_sdk/src/manager/application/addons/addons_provider.dart';
import 'package:products_sdk/src/manager/application/addons/edit/edit_addon_provider.dart';
import 'package:products_sdk/src/manager/application/addons/edit/units/edit_addon_units_provider.dart';
import 'package:base_sdk/src/presentation/components/loading/loading_list.dart';

class AddonsBody extends StatelessWidget {
  final RefreshController addonsController;

  const AddonsBody({super.key, required this.addonsController});

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, child) {
        final state = ref.watch(addonsProvider);
        final event = ref.read(addonsProvider.notifier);
        return state.isLoading
            ? const LoadingList(
                verticalPadding: 16,
                itemBorderRadius: 0,
                itemPadding: 10,
              )
            : SmartRefresher(
                controller: addonsController,
                physics: const NeverScrollableScrollPhysics(),
                enablePullDown: true,
                enablePullUp: true,
                onLoading: () =>
                    event.fetchMoreAddons(refreshController: addonsController),
                onRefresh: () =>
                    event.refreshAddons(refreshController: addonsController),
                child: ListView.builder(
                  physics: const NeverScrollableScrollPhysics(),
                  padding: REdgeInsets.only(top: 16),
                  shrinkWrap: true,
                  itemCount: state.addons.length,
                  itemBuilder: (context, index) => AddonItem(
                    addon: state.addons[index],
                    onTap: () {
                      ref
                          .read(editAddonProvider.notifier)
                          .setAddonDetails(state.addons[index]);
                      ref
                          .read(editAddonUnitsProvider.notifier)
                          .setAddonUnit(state.addons[index].unit);
                      AppHelpers.showCustomModalBottomSheet(
                        paddingTop: 60,
                        context: context,
                        modal: EditAddonModal(addon: state.addons[index]),
                        isDarkMode: false,
                      );
                    },
                  ),
                ),
              );
      },
    );
  }
}
