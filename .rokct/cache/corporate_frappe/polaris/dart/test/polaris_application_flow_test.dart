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

import 'package:polaris_sdk/src/common/application/polaris/polaris_provider.dart';
import 'package:polaris_sdk/src/common/di/polaris_di.dart';
import 'package:polaris_sdk/src/common/domain/bridges/polaris_wallet_bridge.dart';
import 'package:polaris_sdk/src/common/infrastructure/repositories/mock_polaris_repository_impl.dart';
import 'package:polaris_sdk/src/common/infrastructure/services/polaris_draft_storage.dart';
import 'package:polaris_sdk/src/common/models/polaris_models.dart';
import 'package:polaris_sdk/src/common/polaris_sdk_core.dart';
import 'package:polaris_sdk/src/common/presentation/pages/application/polaris_application_page.dart';

class TestWalletBridge implements PolarisWalletBridge {
  @override
  Future<void> onInitiationFeeDebited(double amount, String reference) async {}

  @override
  Future<void> onLoanDisbursed(double amount, String reference) async {}

  @override
  Future<void> onRepaymentReceived(double amount, String reference) async {}
}

/// Draft storage that never touches the shared drift database, which is not
/// available inside widget tests.
class InMemoryDraftStorage extends PolarisDraftStorage {
  LoanApplicationPayload? _draft;

  @override
  Future<void> saveDraft(LoanApplicationPayload payload) async {
    _draft = payload;
  }

  @override
  Future<LoanApplicationPayload?> getDraft() async => _draft;

  @override
  Future<void> clearDraft() async {
    _draft = null;
  }
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
      userPrefill: PolarisUserPrefill(
        firstName: 'John',
        lastName: 'Doe',
        idNumber: '123456789',
        phone: '5551234',
      ),
      repository: MockPolarisRepositoryImpl(),
    );
  });

  testWidgets('PolarisApplicationPage multi-step flow test', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          polarisDraftStorageProvider.overrideWithValue(
            InMemoryDraftStorage(),
          ),
        ],
        child: const MaterialApp(home: PolarisApplicationPage()),
      ),
    );

    // Initial render might take a frame
    await tester.pumpAndSettle();

    // Step 1: Affordability Check
    expect(find.text('Step 1: Affordability Check'), findsOneWidget);

    // Fill in income and expenses to pass affordability
    await tester.enterText(
      find.widgetWithText(TextField, 'Monthly Income (Net)'),
      '20000',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Monthly Living Expenses'),
      '5000',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Other Monthly Debt Obligations'),
      '1000',
    );
    await tester.tap(find.text('Check Affordability'));
    await tester.pumpAndSettle();

    // Step 2: Personal Details
    expect(find.text('Step 2: Personal Details'), findsOneWidget);
    expect(find.text('First Name: John'), findsOneWidget);
    await tester.tap(find.text('Confirm and Continue'));
    await tester.pumpAndSettle();

    // Step 3: Document Upload
    expect(find.text('Step 3: Document Upload'), findsOneWidget);
    // Find all upload buttons and tap them
    final uploadButtons = find.text('Upload');
    expect(uploadButtons, findsNWidgets(4));

    await tester.tap(uploadButtons.first);
    await tester.pumpAndSettle();
    await tester.tap(uploadButtons.first);
    await tester.pumpAndSettle();
    await tester.tap(uploadButtons.first);
    await tester.pumpAndSettle();
    await tester.tap(uploadButtons.first);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    // Step 4: Contract Review
    expect(find.text('Step 4: Contract Review'), findsOneWidget);
    // Simulate scroll to bottom by finding the scrollable and dragging
    await tester.drag(
      find.byType(SingleChildScrollView),
      const Offset(0, -3000),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('I have read and agree to the terms'));
    await tester.pumpAndSettle();

    // Step 5: Consent & Submission
    expect(find.text('Step 5: Consent & Submission'), findsOneWidget);

    // Tap the checkbox using finding by text (its title)
    await tester.tap(find.text('I consent to the DebiCheck mandate.'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Submit Application'));
    // Wait for the mock repository future to complete
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Step 6: Outcome — the mock repository returns a pending application
    expect(find.text('Application Pending'), findsOneWidget);
  });
}
