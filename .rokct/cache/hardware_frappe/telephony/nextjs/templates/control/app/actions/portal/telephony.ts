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

"use server";

import { TelephonyPortalService } from "@/app/services/portal/telephony";
import { revalidatePath } from "next/cache";

// Server actions for the telephony customer portal pages
// (app/portal/telephony/...). Thin wrappers over
// app/services/portal/telephony.ts — see that file for the gateway cmd and
// auth-lane documentation. Endpoint responses keep the source API's
// `{ status, data?, message? }` contract.

export async function getCustomerBalance() {
  return TelephonyPortalService.getCustomerBalance();
}

export async function getUserSubscriptions() {
  return TelephonyPortalService.getUserSubscriptions();
}

export async function getSubscriptionDetails(subscriptionName: string) {
  return TelephonyPortalService.getSubscriptionDetails(subscriptionName);
}

export async function getCallHistory(subscriptionName: string) {
  return TelephonyPortalService.getCallHistory(subscriptionName);
}

export async function cancelSubscription(subscriptionName: string) {
  const res = await TelephonyPortalService.cancelSubscription(subscriptionName);
  revalidatePath("/portal/telephony");
  return res;
}

export async function restartSubscription(subscriptionName: string) {
  const res =
    await TelephonyPortalService.restartSubscription(subscriptionName);
  revalidatePath("/portal/telephony");
  return res;
}

export async function initiateTopUp(amount: number) {
  return TelephonyPortalService.initiateTopUp(amount);
}

export async function getPaymentRequestDetails(token: string) {
  return TelephonyPortalService.getPaymentRequestDetails(token);
}

export async function handlePaystackCallback(reference: string, token: string) {
  const res = await TelephonyPortalService.handlePaystackCallback(
    reference,
    token,
  );
  revalidatePath("/portal/telephony");
  return res;
}

export async function getTelephonyPlans() {
  return TelephonyPortalService.getTelephonyPlans();
}

export async function getAvailableAreaCodes() {
  return TelephonyPortalService.getAvailableAreaCodes();
}

export async function provisionNewService(args: {
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
  return TelephonyPortalService.provisionNewService(args);
}
