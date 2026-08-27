# Polaris SDK

Polaris is the group's microlending product, built as an injectable Flutter SDK. It provides injectable UI cards and a full multi-step loan application journey. Backend management is handled remotely; this SDK calculates breakdowns offline and allows users to apply.

## Features

- **Injectable UI**: Cards like `PolarisLoanStatusCard` and `PolarisApplyCard` that you can place into any host app page.
- **Offline Loan Calculation**: Pure functional breakdown computation without needing network calls.
- **Multi-step Flow**: Full application journey including affordability checks, details confirmation, document uploads (UI), and contract review.
- **State Management**: Uses `flutter_riverpod` internally to persist drafts and synchronize state.

## Integration Principles

The SDK expects to be injected with dependencies during initialization. It avoids directly importing host app components, such as `wallet_sdk` or `auth_sdk`. Instead, it uses bridges and session configurations.

## Getting Started

### 1. Define Bridges

Create instances of `PolarisWalletBridge` in your host application:

```dart
class MyWalletBridge implements PolarisWalletBridge {
  @override
  Future<void> onLoanDisbursed(double amount, String reference) async {
    // Write to your wallet SDK
  }
  // Implement other callbacks...
}
```

### 2. Initialization

Before using Polaris widgets, call `PolarisSDK.initialize` typically after login:

```dart
PolarisSDK.initialize(
  config: PolarisConfig(
    minLoanAmount: 100,
    maxLoanAmount: 5000,
    minTermDays: 7,
    maxTermDays: 30,
    initiationFeeRate: 0.15,
    serviceFeeFlat: 86.00,
    interestRatePerDay: 0.001,
    vatRate: 0.15,
    maxInitiationFee: 1150.00,
  ),
  session: PolarisSession(
    userId: '123',
    authToken: 'token123',
    hasActiveLoan: false,
    isEligibleToApply: true,
  ),
  walletBridge: MyWalletBridge(),
  userPrefill: PolarisUserPrefill(
    firstName: 'Jane',
    lastName: 'Doe',
  ),
);
```

### 3. Inject Cards

Once initialized, inject the cards where needed.

```dart
// In a generic Profile or Wallet page
PolarisApplyCard(
  onApply: () {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => const PolarisApplicationPage(),
    ));
  },
)

PolarisLoanStatusCard()
```

### 4. Updating Session

If a user logs in, out, or their eligibility changes:

```dart
PolarisSDK.instance.onSessionChanged(newSession);
```
