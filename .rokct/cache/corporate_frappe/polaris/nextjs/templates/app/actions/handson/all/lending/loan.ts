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

import { verifyLendingRole, verifyLendingLicense } from "@/app/lib/roles";
import { LoanService } from "@/app/services/all/lending/loan";

export async function getLoans(page = 1, limit = 20, filters: any = {}) {
  if (!(await verifyLendingRole())) {
    if (!(await verifyLendingLicense()))
      return {
        data: [],
        total: 0,
        error: "Company must be a registered Credit Provider.",
      };
    return { data: [], total: 0, error: "Unauthorized" };
  }

  try {
    const result = await LoanService.getList(page, limit, filters);
    return {
      data: result.data,
      total: result.total,
      page: result.page,
      limit: result.limit,
    };
  } catch (e) {
    console.error("Failed to fetch Loans", e);
    return { data: [], total: 0, error: "Failed to fetch loans" };
  }
}

export async function getLoan(id: string) {
  if (!(await verifyLendingRole())) {
    if (!(await verifyLendingLicense()))
      return {
        data: null,
        error: "Company must be a registered Credit Provider.",
      };
    return { data: null, error: "Unauthorized" };
  }

  try {
    const data = await LoanService.get(id);
    return { data };
  } catch (e) {
    return { data: null, error: "Failed to fetch Loan" };
  }
}

export async function getLoanRepaymentSchedule(loanId: string) {
  if (!(await verifyLendingRole())) return [];

  try {
    return await LoanService.getRepaymentSchedule(loanId);
  } catch (e) {
    return [];
  }
}

// getAssetAccounts() removed - see the matching comment in
// app/services/all/lending/loan.ts for why (ERPNext Account dependency,
// resolved by switching the asset-realisation picker to free text).

export async function realisePawnAsset({
  loan,
  asset_account,
}: {
  loan: string;
  asset_account: string;
}) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const message = await LoanService.realisePawnAsset(loan, asset_account);
    return { success: true, message };
  } catch (e: any) {
    console.error("Asset Realisation Failed", e);
    return { success: false, error: e.message || "Failed to realise asset" };
  }
}

export async function disburseLoan({
  loanId,
  postingDate,
}: {
  loanId: string;
  postingDate?: string;
}) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const message = await LoanService.disburse(loanId, postingDate);
    return { success: true, message };
  } catch (e: any) {
    console.error("Disbursement Failed", e);
    return { success: false, error: e.message || "Failed to disburse loan" };
  }
}

export async function releaseSecurity({ loanId }: { loanId: string }) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };
  try {
    const message = await LoanService.releaseSecurity(loanId);
    return { success: true, message };
  } catch (e: any) {
    console.error("Release Failed", e);
    return { success: false, error: e.message || "Failed to release security" };
  }
}

export async function getLoanTimeline(loanId: string) {
  if (!(await verifyLendingRole())) return [];

  try {
    return await LoanService.getTimeline(loanId);
  } catch (e) {
    console.error("Failed to fetch Timeline", e);
    return [];
  }
}
