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

import { revalidatePath } from "next/cache";
import { verifyLendingRole, verifyLendingLicense } from "@/app/lib/roles";
import { z } from "zod";
import { ApplicationService } from "@/app/services/all/lending/application";

const LoanApplicationSchema = z.object({
  applicant_type: z.enum(["Employee", "Customer", "Member"]),
  applicant: z.string().min(1, "Applicant is required"),
  company: z.string().min(1, "Company is required"),
  loan_product: z.string().min(1, "Loan Product is required"),
  loan_amount: z.number().positive("Loan amount must be positive"),
  description: z.string().optional(), // Used for Asset/Collateral Description in Pawn Loans
  is_secured_loan: z.number().optional(),
  repayment_method: z
    .enum(["Repay Fixed Amount per Period", "Repay Over Number of Periods"])
    .optional(),
  repayment_periods: z.number().int().positive().optional(),
  repayment_amount: z.number().positive().optional(),
});

export type LoanApplicationData = z.infer<typeof LoanApplicationSchema>;

export async function getLoanApplications(page = 1, limit = 20) {
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
    const result = await ApplicationService.getList(page, limit);
    return {
      data: result.data,
      total: result.total,
      page: result.page,
      limit: result.limit,
    };
  } catch (e) {
    console.error("Failed to fetch Loan Applications", e);
    return { data: [], total: 0, error: "Failed to fetch applications" };
  }
}

export async function getLoanApplication(id: string) {
  if (!(await verifyLendingRole()))
    return { data: null, error: "Unauthorized" };

  try {
    const data = await ApplicationService.get(id);
    return { data };
  } catch (e) {
    return { data: null, error: "Failed to fetch Loan Application" };
  }
}

export async function createLoanApplication(data: LoanApplicationData) {
  if (!(await verifyLendingRole())) {
    if (!(await verifyLendingLicense()))
      return {
        success: false,
        error: "Company must be a registered Credit Provider.",
      };
    return { success: false, error: "Unauthorized" };
  }

  const validation = LoanApplicationSchema.safeParse(data);
  if (!validation.success) {
    return { success: false, error: validation.error.issues[0].message };
  }

  try {
    const result = await ApplicationService.create(data);
    revalidatePath("/handson/all/lending/application");
    return { success: true, message: result };
  } catch (e: any) {
    console.error("Create Loan App Error", e);
    return {
      success: false,
      error: e?.message || "Error creating application",
    };
  }
}

export async function updateLoanApplication(
  name: string,
  data: Partial<LoanApplicationData>,
) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const result = await ApplicationService.update(name, data);
    revalidatePath("/handson/all/lending/application");
    revalidatePath(`/handson/all/lending/application/${name}`);
    return { success: true, message: result };
  } catch (e: any) {
    return {
      success: false,
      error: e?.message || "Error updating application",
    };
  }
}
