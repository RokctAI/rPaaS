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
import { OperationsService } from "@/app/services/all/lending/operations";

export async function triggerLoanInterestAccrual(postingDate?: string) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const message = await OperationsService.triggerInterestAccrual(postingDate);
    return { success: true, message: `Interest Accrual Processed: ${message}` };
  } catch (e: any) {
    console.error("Interest Accrual Failed", e);
    return {
      success: false,
      error: e.message || "Failed to trigger interest accrual",
    };
  }
}

export async function triggerLoanSecurityShortfall() {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    await OperationsService.triggerSecurityShortfall();
    return { success: true, message: "Security Shortfall Check Initiated" };
  } catch (e: any) {
    console.error("Shortfall Check Failed", e);
    return {
      success: false,
      error: e.message || "Failed to trigger shortfall check",
    };
  }
}

export async function triggerLoanClassification() {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    await OperationsService.triggerClassification();
    return { success: true, message: "Loan Classification Process Initiated" };
  } catch (e: any) {
    console.error("Classification Failed", e);
    return {
      success: false,
      error: e.message || "Failed to trigger classification",
    };
  }
}

export async function getProcessLogs(limit = 10) {
  if (!(await verifyLendingRole())) return [];
  try {
    return await OperationsService.getProcessLogs(limit);
  } catch (e) {
    console.error("Failed to fetch logs", e);
    return [];
  }
}
