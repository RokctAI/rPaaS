# PaaS Module Development Guide

> **Status note (2026-08-23):** This guide dates from the monorepo era (January 2026). Several paths it references (`paas/juvo/`, `/analyze`, `TODO.md`, `roadmap_progress.txt`, `paas/api/`) no longer exist in this repository. The sections below are kept for historical context, with dated status notes where functionality has since been superseded by the split SDK repositories.

This document provides architectural guidelines and instructions for developers working on the `PaaS` module of the ROKCT application.

## Core Architectural Principle

The primary architectural approach for this module is to **extend existing Frappe functionality** wherever possible, rather than creating new, separate modules for core concepts.

For example, when adding features related to user management, we should extend the standard Frappe `User` doctype with custom fields. A separate, custom "User Management" module should only be created if the features are fundamentally different from the core `User` concept and cannot be achieved through extension. This principle applies to other core features as well.

## Development Priority & API Conversion

The immediate priority is to **convert the existing Laravel backend** into Frappe/ROKCT. The goal is to replicate the Laravel API contract perfectly within the Frappe backend.

This will allow the various frontend applications (Flutter, React) to be switched over to the new Frappe backend simply by changing their base URL. This minimizes the need for changes in the frontend applications.

## Codebase for Analysis

> **Status note (2026-08-23):** The `paas/juvo/` directory (and the `/analyze` directory referenced below) is not present in this repository; the original Laravel/Flutter/React sources were part of the monorepo and were not carried over.

To facilitate the conversion, the source code for the original applications will be placed in the `paas/juvo/` directory:

*   `paas/juvo/backend/`: Contains the source code for the original Laravel backend. **This should be your primary reference for the API conversion.**
*   `paas/juvo/frontend/`: The ReactJS admin frontend.
*   `paas/juvo/customer/`: The Flutter customer/user mobile app.
*   `paas/juvo/manager/`: The Flutter manager mobile app.
*   `paas/juvo/pos/`: The Flutter Point-of-Sale (POS) mobile app.
*   `paas/juvo/web/`: The customer-facing web application.
*   `paas/juvo/driver/`: The Flutter driver mobile app.

**Important:** Before starting work, developers **must** first analyze the relevant codebase in `paas/juvo/`. If you need to understand the behavior of the core Frappe framework or other installed apps, you can refer to the code in the `/analyze` directory at the root of the repository. This will provide direct access to the code and help avoid guesswork.

## Completed & Excluded Features

*   **Completed:** The **Weather Feature** has been fully implemented and is functional. It should not be worked on again.
*   **Excluded:** The features related to **"erpgo"** and **"sling" / "slingbolt"** are considered unfinished and are out of scope for the current conversion effort. Do not work on these features.

## Roadmap for Juvo Conversion

A `Roadmap` DocType has been created to track the progress of the Juvo application conversion. This roadmap is for internal use on the control panel only and is not a feature intended for tenants. The roadmap data is used to manage the development and conversion process.

*   **Excluded:** The **Roadmap Feature** is not a user-facing feature for tenants.

## Project Tracking & Documentation

> **Status note (2026-08-23):** `TODO.md` and `roadmap_progress.txt` do not exist in this repository; they were monorepo-era tracking files.

To maintain clarity on the project's progress, we use several key documents. It is crucial that these files are kept synchronized to provide a consistent view of the development status.

*   **`TODO.md`**: This file contains a high-level list of active and pending tasks. It serves as a quick reference for what needs to be worked on next. For complex features, it may link to a more detailed status report.
*   **`roadmap_progress.txt`**: This is the master checklist for the entire Laravel-to-Frappe conversion. It provides a granular, feature-by-feature view of the project's overall progress.
*   **Feature Status Reports (e.g., `PARCEL_DELIVERY_STATUS.md`)**: For large, complex features, a dedicated status report may be created. These documents provide a detailed breakdown of the feature, comparing the original implementation with the new one and outlining what is missing.

**Synchronization Guideline:** When you update the status of a task (e.g., in `TODO.md`), you **must** ensure that the corresponding items in `roadmap_progress.txt` are also updated. This ensures that both the high-level and granular views of our progress remain aligned.

## Feature Activation & Custom Implementation

Certain functionality in PaaS (Lending, Billing, Verification) is designed to be pluggable. By default, these features are disabled or stubbed. To activate them, you must implement the required logic in your own **custom Frappe app**.

### 1. Lending Module

> **Status note (2026-08-23): SUPERSEDED BY the polaris SDK** (corporate repo, `corporate/polaris`). The shipped lending fork provides the full loan doctype suite (`polaris/frappe/src/tenant/doctype/loan*`, `loan_application`, `loan_repayment`, etc.) and the API surface specced below: `disburse_loan` in `polaris/frappe/src/tenant/api/loan.py`, with `create_loan_application`, `disburse_loan`, and `get_my_loan_applications` in `polaris/frappe/src/tenant/api/lending_mocks.py`. `request_payout` is covered by the pay SDK's wallet module (`pay/wallet` — `Platform Wallet.request_payout`, which calls the control plane). The `rcore.rlending` namespace and `paas/api/__init__.py` referenced below no longer exist in this repository.

* **Status**: Disabled (Python dependencies missing).
* **Requirement**: Implement the following methods in your custom app to handle loan logic.
* **Integration**:
    * Current implementation expects `rcore.rlending.api`.
    * **Action**: You must either alias your custom module to this namespace or update `paas/api/__init__.py` to import from your custom app (e.g., `from my_app.lending.api import ...`).
    * **Methods to Implement**:
        - `create_loan_application(applicant_type, applicant, loan_product, ...)`
        - `disburse_loan(loan_application)`
        - `get_my_loan_applications()`
        - `request_payout(amount)`

### 2. Billing & Payments

> **Status note (2026-08-23): SUPERSEDED BY the control repo's billing API plus the pay SDK.** All three endpoints specced below are now hosted by the control app: `control/control/api/billing/get_tenant_wallet_balance.py`, `control/control/api/billing/request_tenant_payout.py`, and `charge_customer_for_addon` in `control/control/billing.py` (mapped in `control/hooks.py`). Tenant-side wallet, payments, and gateway functionality lives in the pay SDK (`pay/wallet`, `pay/payments`, `pay/gateways`). No custom backend service needs to be built.

* **Status**: Disabled (Missing Control Plane configuration).
* **Requirement**: A backend service (Frappe app or external) to handle wallet balances and payment processing.
* **Integration**:
    * PaaS communicates via HTTP. Update `site_config.json` with your custom service URL:
      ```json
      {
       "control_plane_url": "api.your-service.com",
       "api_secret": "your-api-secret"
      }
      ```
    * **Endpoints to Host**:
      - `POST /api/method/control.control.api.billing.get_tenant_wallet_balance`
      - `POST /api/method/control.control.api.billing.request_tenant_payout`
      - `POST /api/method/control.control.billing.charge_customer_for_addon`

### 3. User Verification

> **Status note (2026-08-23): SUPERSEDED BY the users SDK.** Email verification is now handled by an OTP-based flow in `users/frappe/src/tenant/api/user/user.py` (`verify_email_code`), replacing the token-link approach specced below. Related identity/KYC tracking exists in the CRM SDK (productivity repo — `kyc_status` field on the Lead doctype), but that covers KYC state, not email verification. The `paas/api/user/user.py` file referenced below no longer exists in this repository.

* **Status**: Broken Link (Points to missing method).
* **Requirement**: A method to handle email verification tokens.
* **Integration**:
    * **Action**: Update the method reference in `paas/api/user/user.py`:
      ```python
      # Change this to point to your custom app's verification method
      verification_url = frappe.utils.get_url_to_method(
          "my_custom_app.api.verify_email", {"token": token}
      )
      ```

### 4. Seed Data
* **Status**: Empty Database.
* **Requirement**: JSON data files for Shops, Products, and Config.
* **Action**: Create a `seeds/` directory in your custom app and write a script to populate standard data if needed.
