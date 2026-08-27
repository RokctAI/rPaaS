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

import { ControlBaseService } from "./base";

// Admin service for the telephony doctypes. Queries here are aligned to the
// REAL doctype schemas (telephony SDK, hardware/telephony/frappe/src/control/doctype/):
//
// - Telephony Settings is a SINGLE doctype (issingle=1; fields: sip_domain,
//   default_currency, porta_billing_api_url, porta_billing_api_token) — read
//   via frappe.client.get, never get_list. The old frontend queried
//   `provider`/`api_key`, neither of which ever existed.
//   `porta_billing_api_token` is a Password field and is intentionally never
//   fetched or displayed.
// - Telephony Customer fields: user, customer_name, email, phone_number,
//   address, balance. The old frontend queried `status`, which does not
//   exist on this doctype — dropped (balance is listed instead).
// - Telephony Transaction fields: customer, transaction_type, amount,
//   status, transaction_date. The old frontend queried `type`/`date` —
//   the real fieldnames are `transaction_type`/`transaction_date`.
// - Available DID fields: did_number, area_code, is_assigned. The old
//   frontend queried `country`/`status` — the real fieldnames are
//   `area_code`/`is_assigned` (a 0/1 Check).

export class TelephonyService {
  static async getTelephonySettings() {
    // Single doctype: its one document is named after the doctype itself.
    return ControlBaseService.getDoc("Telephony Settings", "Telephony Settings");
  }

  static async getTelephonyCustomers() {
    return ControlBaseService.getList("Telephony Customer", {
      fields: ["name", "customer_name", "phone_number", "balance"],
      order_by: "modified desc",
    });
  }

  static async getTelephonySubscriptions() {
    return ControlBaseService.getList("Telephony Subscription", {
      fields: ["name", "customer", "plan", "status"],
      order_by: "modified desc",
    });
  }

  static async getTelephonyTransactions() {
    return ControlBaseService.getList("Telephony Transaction", {
      fields: ["name", "transaction_type", "amount", "transaction_date"],
      order_by: "transaction_date desc",
    });
  }

  static async getAvailableDIDs() {
    return ControlBaseService.getList("Available DID", {
      fields: ["name", "did_number", "area_code", "is_assigned"],
      order_by: "modified desc",
    });
  }

  static async updateTelephonySettings(data: any) {
    // Single doctype: frappe.client.set_value addresses it by its own name.
    return ControlBaseService.update(
      "Telephony Settings",
      "Telephony Settings",
      data,
    );
  }

  static async createTelephonyCustomer(data: any) {
    return ControlBaseService.insert({
      doctype: "Telephony Customer",
      ...data,
    });
  }

  static async updateTelephonyCustomer(name: string, data: any) {
    return ControlBaseService.update("Telephony Customer", name, data);
  }

  static async deleteTelephonyCustomer(name: string) {
    return ControlBaseService.delete("Telephony Customer", name);
  }

  static async createTelephonySubscription(data: any) {
    return ControlBaseService.insert({
      doctype: "Telephony Subscription",
      ...data,
    });
  }

  static async updateTelephonySubscription(name: string, data: any) {
    return ControlBaseService.update("Telephony Subscription", name, data);
  }

  static async deleteTelephonySubscription(name: string) {
    return ControlBaseService.delete("Telephony Subscription", name);
  }

  static async createAvailableDID(data: any) {
    return ControlBaseService.insert({ doctype: "Available DID", ...data });
  }

  static async updateAvailableDID(name: string, data: any) {
    return ControlBaseService.update("Available DID", name, data);
  }

  static async deleteAvailableDID(name: string) {
    return ControlBaseService.delete("Available DID", name);
  }
}
