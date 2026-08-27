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

﻿import 'package:flutter_test/flutter_test.dart';
import 'package:polaris_sdk/src/common/models/polaris_models.dart';
import 'package:polaris_sdk/src/common/application/polaris/loan_calculator.dart';

void main() {
  group('LoanCalculator', () {
    final config = PolarisConfig(
      minLoanAmount: 100,
      maxLoanAmount: 5000,
      minTermDays: 7,
      maxTermDays: 30,
      initiationFeeRate: 0.15,
      serviceFeeFlat: 86.00,
      interestRatePerDay: 0.001,
      vatRate: 0.15,
      maxInitiationFee: 1150.00,
    );

    test('calculates correct breakdown for standard inputs', () {
      final breakdown = LoanCalculator.calculateBreakdown(
        amount: 1000,
        termDays: 14,
        config: config,
      );

      expect(breakdown.capital, 1000);
      expect(breakdown.initiationFee, 150); // 1000 * 0.15
      expect(breakdown.serviceFee, 86);
      expect(breakdown.interest, 14); // 1000 * 0.001 * 14
      expect(breakdown.vat, closeTo(35.4, 0.01)); // (150 + 86) * 0.15

      final expectedTotal = 1000 + 150 + 86 + 14 + 35.4;
      expect(breakdown.totalRepayable, closeTo(expectedTotal, 0.01));
    });

    test('clamps amount and term to minimums', () {
      final breakdown = LoanCalculator.calculateBreakdown(
        amount: 50, // Below min 100
        termDays: 5, // Below min 7
        config: config,
      );

      expect(breakdown.capital, 100);

      final expectedInterest = 100 * 0.001 * 7;
      expect(breakdown.interest, expectedInterest);
    });

    test('clamps amount and term to maximums', () {
      final breakdown = LoanCalculator.calculateBreakdown(
        amount: 10000, // Above max 5000
        termDays: 60, // Above max 30
        config: config,
      );

      expect(breakdown.capital, 5000);

      final expectedInterest = 5000 * 0.001 * 30;
      expect(breakdown.interest, expectedInterest);
    });

    test('caps initiation fee to maxInitiationFee', () {
      final breakdown = LoanCalculator.calculateBreakdown(
        amount: 5000,
        termDays: 30,
        config: config,
      );

      // 5000 * 0.15 = 750, which is < 1150, so it shouldn't be capped here.
      expect(breakdown.initiationFee, 750);

      // Let's test a config where it would cap
      final capConfig = PolarisConfig(
        minLoanAmount: 100,
        maxLoanAmount: 10000,
        minTermDays: 7,
        maxTermDays: 30,
        initiationFeeRate: 0.20,
        serviceFeeFlat: 86.00,
        interestRatePerDay: 0.001,
        vatRate: 0.15,
        maxInitiationFee: 1000.00,
      );

      final capBreakdown = LoanCalculator.calculateBreakdown(
        amount: 10000,
        termDays: 30,
        config: capConfig,
      );

      // 10000 * 0.20 = 2000 > 1000, so it caps at 1000
      expect(capBreakdown.initiationFee, 1000);
    });
  });
}

