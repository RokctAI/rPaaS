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

import { verifyLendingRole } from "@/app/lib/roles";
import { LifecycleService } from "@/app/services/all/lending/lifecycle";

export async function createLoanWriteOff(loan: string, amount: number) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const res = await LifecycleService.createLoanWriteOff(loan, amount);
    return { success: true, message: `Acc. ${loan} Written Off (${res.name})` };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

export async function createLoanRestructure(data: {
  loan: string;
  date: string;
  reason?: string;
  // Simple restructure params (usually just modifying terms)
  new_term_months?: number;
  new_interest_rate?: number;
}) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };
  try {
    const res = await LifecycleService.createLoanRestructure(data);
    return { success: true, message: `Loan Restructured (${res.name})` };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

export async function createBalanceAdjustment(data: {
  loan: string;
  amount: number;
  type: "Debit Adjustment" | "Credit Adjustment";
  remarks?: string;
}) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };
  try {
    const res = await LifecycleService.createBalanceAdjustment(data);
    return { success: true, message: `Adjustment Posted (${res.name})` };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}
