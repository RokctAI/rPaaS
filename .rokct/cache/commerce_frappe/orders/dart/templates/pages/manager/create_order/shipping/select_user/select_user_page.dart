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
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'widgets/user_item.dart';
import 'widgets/create_user_modal.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/presentation/components/app_bars/custom_app_bar.dart';
import 'package:base_sdk/src/constants/app_constants.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/components/keyboard_dismisser.dart';
import 'package:base_sdk/src/presentation/components/text_fields/search_text_field.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:orders_sdk/src/manager/application/order/shipping/user/order_user_provider.dart';


@RoutePage(name: 'ManagerSelectUserRoute')
class SelectUserPage extends ConsumerStatefulWidget {
  const SelectUserPage({super.key});

  @override
  ConsumerState<SelectUserPage> createState() => _SelectUserPageState();
}

class _SelectUserPageState extends ConsumerState<SelectUserPage> {
  late RefreshController _refreshController;

  @override
  void initState() {
    super.initState();
    _refreshController = RefreshController();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref
          .read(orderUserProvider.notifier)
          .initialFetchUsers(refreshController: _refreshController),
    );
  }

  @override
  void dispose() {
    super.dispose();
    _refreshController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardDismisser(
      child: Scaffold(
        backgroundColor: AppStyle.bgGrey,
        body: Consumer(
          builder: (context, ref, child) {
            final state = ref.watch(orderUserProvider);
            final event = ref.read(orderUserProvider.notifier);
            return Column(
              children: [
                CustomAppBar(
                  bottomPadding: 4.h,
                  child: SearchTextField(
                    onChanged: (value) => event.setQuery(
                      refreshController: _refreshController,
                      text: value,
                    ),
                  ),
                ),
                state.isLoading
                    ? Center(
                        child: Container(
                          margin: REdgeInsets.only(top: 30),
                          width: 30.r,
                          height: 30.r,
                          child: CircularProgressIndicator(
                            strokeWidth: 3.r,
                            color: AppStyle.blackColor,
                          ),
                        ),
                      )
                    : Expanded(
                        child: SmartRefresher(
                          controller: _refreshController,
                          enablePullUp: true,
                          onRefresh: () => event.refreshUsers(
                            refreshController: _refreshController,
                          ),
                          onLoading: () => event.fetchMoreUsers(
                            refreshController: _refreshController,
                          ),
                          child: ListView.builder(
                            physics: const BouncingScrollPhysics(),
                            itemCount: state.users.length,
                            shrinkWrap: true,
                            padding: REdgeInsets.only(
                              left: 16,
                              right: 16,
                              top: 20,
                              bottom: 80,
                            ),
                            itemBuilder: (context, index) => UserItem(
                              user: state.users[index],
                              isSelected: index == state.selectedIndex,
                              onTap: () {
                                event.setSelectedUser(index);
                                context.maybePop(state.users[index].phone);
                              },
                            ),
                          ),
                        ),
                      ),
              ],
            );
          },
        ),
        floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
        floatingActionButton: Padding(
          padding: REdgeInsets.all(16),
          child: Row(
            children: [
              const PopButton(heroTag: AppConstants.heroTagAddOrderButton),
              8.horizontalSpace,
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.addUser),
                  onPressed: () => AppHelpers.showCustomModalBottomSheet(
                    context: context,
                    modal: const CreateUserModal(),
                    isDarkMode: true,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
