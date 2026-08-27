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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get_it/get_it.dart';

import 'package:polaris_sdk/src/common/di/polaris_di.dart';
import 'package:polaris_sdk/src/common/domain/bridges/polaris_wallet_bridge.dart';
import 'package:polaris_sdk/src/common/infrastructure/repositories/mock_polaris_repository_impl.dart';
import 'package:polaris_sdk/src/common/models/polaris_models.dart';
import 'package:polaris_sdk/src/common/polaris_sdk_core.dart';
import 'package:polaris_sdk/src/common/presentation/widgets/polaris_apply_card.dart';

class TestWalletBridge implements PolarisWalletBridge {
  @override
  Future<void> onInitiationFeeDebited(double amount, String reference) async {}

  @override
  Future<void> onLoanDisbursed(double amount, String reference) async {}

  @override
  Future<void> onRepaymentReceived(double amount, String reference) async {}
}

void main() {
  setUp(() {
    PolarisSdkDependencies.register(GetIt.instance);
    PolarisSDK.initialize(
      config: PolarisConfig(
        minLoanAmount: 100,
        maxLoanAmount: 5000,
        minTermDays: 7,
        maxTermDays: 30,
        initiationFeeRate: 0.15,
        serviceFeeFlat: 86.0,
        interestRatePerDay: 0.001,
        vatRate: 0.15,
        maxInitiationFee: 1150.0,
      ),
      session: PolarisSession(
        userId: 'test_user',
        authToken: 'token',
        hasActiveLoan: false,
        isEligibleToApply: true,
      ),
      walletBridge: TestWalletBridge(),
      userPrefill: PolarisUserPrefill(),
      repository: MockPolarisRepositoryImpl(),
    );
  });

  testWidgets('PolarisApplyCard renders collapsed state initially', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: PolarisApplyCard(onApply: () {})),
        ),
      ),
    );

    // Initial render might have sliders but no expanded breakdown
    expect(find.text('Need a loan?'), findsOneWidget);
    expect(find.text('Amount'), findsOneWidget);
    expect(find.text('Term'), findsOneWidget);

    // Should not see Total Repayable yet because it's not expanded
    expect(find.text('Total Repayable:'), findsNothing);
  });

  testWidgets('PolarisApplyCard expands on slider interaction', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: PolarisApplyCard(onApply: () {})),
        ),
      ),
    );

    // Find the first slider (Amount)
    final sliderFinder = find.byType(Slider).first;

    // Interact with it
    await tester.tap(sliderFinder);
    await tester.pumpAndSettle();

    // Now breakdown should be visible
    expect(find.text('Total Repayable:'), findsOneWidget);
    expect(find.text('Apply Now'), findsOneWidget);
  });
}
