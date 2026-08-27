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
import 'package:remixicon/remixicon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import 'package:base_sdk/src/presentation/components/app_bars/common_app_bar.dart';
import 'package:base_sdk/src/presentation/components/buttons/custom_button.dart';
import 'package:base_sdk/src/presentation/components/buttons/pop_button.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';
import 'package:base_sdk/src/services/app_helpers.dart';
import 'package:base_sdk/src/services/tr_keys.dart';
import 'package:merchants_sdk/src/manager/application/sync_issues/sync_issues_provider.dart';
import 'package:merchants_sdk/src/manager/infrastructure/services/sync_issues_service.dart';

// Sync-issues screen (park-and-surface, offline-first Phase 2): lists the
// parked `needs_attention` records across the three manager local-first
// boxes with the server's rejection message, and resolves each with Retry
// (requeue the queued push as-is) or Discard (delete record + outbox op).
// State lives in the SDK at lib/src/manager/application/sync_issues/
// (syncIssuesProvider over SyncIssuesService); this installed page is only
// the presentation shell, per the restaurant-tab convention.
@RoutePage(name: 'ManagerSyncIssuesRoute')
class SyncIssuesPage extends ConsumerStatefulWidget {
  const SyncIssuesPage({super.key});

  @override
  ConsumerState<SyncIssuesPage> createState() => _SyncIssuesPageState();
}

class _SyncIssuesPageState extends ConsumerState<SyncIssuesPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(syncIssuesProvider.notifier).fetch(),
    );
  }

  /// Box name -> what the record is, via base TrKeys (`shop` / `product` /
  /// `order`); the box name itself is the tolerant fallback.
  String _boxLabel(String box) {
    switch (box) {
      case 'manager_shops':
        return AppHelpers.getTranslation(TrKeys.shop);
      case 'manager_products':
        return AppHelpers.getTranslation(TrKeys.product);
      case 'manager_orders':
        return AppHelpers.getTranslation(TrKeys.order);
    }
    return box;
  }

  IconData _boxIcon(String box) {
    switch (box) {
      case 'manager_shops':
        return Remix.store_2_line;
      case 'manager_products':
        return Remix.shopping_bag_3_line;
      case 'manager_orders':
        return Remix.file_list_3_line;
    }
    return Remix.error_warning_line;
  }

  Future<void> _retry(SyncIssue issue) async {
    final retried = await ref.read(syncIssuesProvider.notifier).retry(issue);
    if (!mounted) return;
    // On success the row leaves the list (record back to pending_sync) —
    // that refresh is the feedback. Failure means no queued op was left to
    // requeue; the record stays parked and only discard resolves it.
    if (!retried) {
      AppHelpers.showCheckTopSnackBar(
        context,
        AppHelpers.getTranslation(TrKeys.somethingWentWrongWithTheServer),
      );
    }
  }

  void _confirmDiscard(SyncIssue issue) {
    AppHelpers.showAlertDialog(
      context: context,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppHelpers.getTranslation(TrKeys.areYouSure),
            style: AppStyle.interNormal(
              size: 14.sp,
              color: AppStyle.blackColor,
            ),
            textAlign: TextAlign.center,
          ),
          24.verticalSpace,
          Row(
            children: [
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.cancel),
                  background: AppStyle.transparent,
                  borderColor: AppStyle.borderColor,
                  onPressed: () => Navigator.pop(context),
                ),
              ),
              16.horizontalSpace,
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.discard),
                  background: AppStyle.red,
                  textColor: AppStyle.white,
                  onPressed: () {
                    Navigator.pop(context);
                    ref.read(syncIssuesProvider.notifier).discard(issue);
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(syncIssuesProvider);
    return Scaffold(
      backgroundColor: AppStyle.bgGrey,
      body: Column(
        children: [
          CommonAppBar(
            child: Text(
              AppHelpers.getTranslation(TrKeys.syncIssues),
              style: AppStyle.interSemi(size: 18.sp),
            ),
          ),
          Expanded(
            child: state.isLoading && state.issues.isEmpty
                ? const Center(child: CircularProgressIndicator.adaptive())
                : state.issues.isEmpty
                ? _empty()
                : RefreshIndicator.adaptive(
                    onRefresh: () =>
                        ref.read(syncIssuesProvider.notifier).fetch(),
                    child: ListView.builder(
                      physics: const AlwaysScrollableScrollPhysics(
                        parent: BouncingScrollPhysics(),
                      ),
                      padding: REdgeInsets.only(
                        left: 16,
                        right: 16,
                        top: 16,
                        bottom: 100,
                      ),
                      itemCount: state.issues.length,
                      itemBuilder: (context, index) =>
                          _issueItem(state.issues[index]),
                    ),
                  ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: const PopButton(),
    );
  }

  Widget _empty() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Remix.checkbox_circle_line,
            size: 48.r,
            color: AppStyle.textGrey,
          ),
          12.verticalSpace,
          Text(
            AppHelpers.getTranslation(TrKeys.noData),
            style: AppStyle.interNormal(size: 14.sp, color: AppStyle.textGrey),
          ),
        ],
      ),
    );
  }

  Widget _issueItem(SyncIssue issue) {
    return Container(
      margin: REdgeInsets.only(bottom: 12),
      padding: REdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppStyle.white,
        borderRadius: BorderRadius.circular(10.r),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_boxIcon(issue.box), size: 20.r, color: AppStyle.blackColor),
              8.horizontalSpace,
              Text(
                _boxLabel(issue.box),
                style: AppStyle.interSemi(
                  size: 12.sp,
                  color: AppStyle.textGrey,
                ),
              ),
            ],
          ),
          8.verticalSpace,
          Text(
            issue.summary,
            style: AppStyle.interSemi(size: 16.sp, color: AppStyle.blackColor),
          ),
          if (issue.error != null && issue.error!.isNotEmpty) ...[
            6.verticalSpace,
            Text(
              issue.error!,
              style: AppStyle.interNormal(size: 13.sp, color: AppStyle.red),
            ),
          ],
          16.verticalSpace,
          Row(
            children: [
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.tryAgain),
                  onPressed: () => _retry(issue),
                ),
              ),
              16.horizontalSpace,
              Expanded(
                child: CustomButton(
                  title: AppHelpers.getTranslation(TrKeys.discard),
                  background: AppStyle.transparent,
                  textColor: AppStyle.red,
                  borderColor: AppStyle.red,
                  onPressed: () => _confirmDiscard(issue),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
