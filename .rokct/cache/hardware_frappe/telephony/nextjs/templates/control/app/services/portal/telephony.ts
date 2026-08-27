/*
 * Copyright (c) 2026 RokctAI
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { ControlBaseService } from "@/app/services/control/base";
import { getGuestClient, getSystemControlClient } from "@/app/lib/client";
import { gatewayCall } from "@/app/lib/gateway-rpc";

// Customer-portal service for the telephony product — the Next.js successor
// of the transitional Frappe web pages (telephony SDK,
// hardware/telephony/frappe/src/templates/pages/ and src/www/). Every call
// goes through the universal platform gateway (ADR-005: single
// `{cmd, payload}` POST, never bare per-method URLs) against the telephony
// SDK's whitelisted control-side endpoints, addressed by their registered
// `control:<name>` gateway cmds.
//
// Three auth lanes, chosen per endpoint to match the source pages' own
// semantics:
//
// - Session-scoped endpoints (get_customer_balance, get_user_subscriptions,
//   get_subscription_details, initiate_top_up, cancel/restart_subscription,
//   get_call_history) derive the customer from frappe.session.user, so they
//   ride ControlBaseService — the logged-in user's OWN api key/secret from
//   the NextAuth session (app/lib/client.ts getControlClient), exactly as
//   the Frappe pages ran them under the visitor's website session.
// - Guest, token-scoped checkout endpoints (get_payment_request_details,
//   handle_paystack_callback — both allow_guest server-side) ride the guest
//   client: no credentials, the token is the capability, matching the
//   public /paystack_checkout Frappe page.
// - Public signup data (plan list, area codes) and provisioning were
//   rendered/invoked by the Frappe signup page with server-side website
//   context; their Next.js analogue is the shell's system identity
//   (getSystemControlClient), because the signup visitor has no account yet.

const unwrap = (res: any) =>
  res && typeof res === "object" && "message" in res ? res.message : res;

export class TelephonyPortalService {
  // ---- Logged-in customer (session-scoped) ----

  static async getCustomerBalance() {
    return unwrap(await ControlBaseService.call("control:get_customer_balance"));
  }

  static async getUserSubscriptions() {
    return unwrap(
      await ControlBaseService.call("control:get_user_subscriptions"),
    );
  }

  static async getSubscriptionDetails(subscriptionName: string) {
    return unwrap(
      await ControlBaseService.call("control:get_subscription_details", {
        subscription_name: subscriptionName,
      }),
    );
  }

  static async getCallHistory(subscriptionName: string) {
    return unwrap(
      await ControlBaseService.call("control:get_call_history", {
        subscription_name: subscriptionName,
      }),
    );
  }

  static async cancelSubscription(subscriptionName: string) {
    return unwrap(
      await ControlBaseService.call("control:cancel_subscription", {
        subscription_name: subscriptionName,
      }),
    );
  }

  static async restartSubscription(subscriptionName: string) {
    return unwrap(
      await ControlBaseService.call("control:restart_subscription", {
        subscription_name: subscriptionName,
      }),
    );
  }

  static async initiateTopUp(amount: number) {
    return unwrap(
      await ControlBaseService.call("control:initiate_top_up", { amount }),
    );
  }

  // ---- Guest checkout (token-scoped, allow_guest server-side) ----

  static async getPaymentRequestDetails(token: string) {
    const client = getGuestClient();
    return unwrap(
      await gatewayCall(client, "control:get_payment_request_details", {
        token,
      }),
    );
  }

  static async handlePaystackCallback(reference: string, token: string) {
    const client = getGuestClient();
    return unwrap(
      await gatewayCall(client, "control:handle_paystack_callback", {
        reference,
        token,
      }),
    );
  }

  // ---- Public signup (served under the shell's system identity) ----

  static async getTelephonyPlans() {
    const client = await getSystemControlClient();
    return unwrap(
      await gatewayCall(client, "frappe.client.get_list", {
        doctype: "Subscription Plan",
        filters: { plan_category: "Telephony" },
        fields: [
          "name",
          "plan_name",
          "cost",
          "billing_cycle",
          "is_per_seat_plan",
          "base_user_count",
        ],
      }),
    );
  }

  static async getAvailableAreaCodes() {
    const client = await getSystemControlClient();
    return unwrap(
      await gatewayCall(client, "control:get_available_area_codes"),
    );
  }

  static async provisionNewService(args: {
    plan: string;
    lines: number;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    company_name: string;
    currency: string;
    country: string;
    industry: string;
    area_code: string;
  }) {
    // Registered by this SDK's manifest: control:provision_new_service ->
    // {app_name}.telephony.control.api.provisioning.provision_new_service.
    const client = await getSystemControlClient();
    return unwrap(
      await gatewayCall(client, "control:provision_new_service", args),
    );
  }
}
