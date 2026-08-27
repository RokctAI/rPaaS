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
import { DemandService } from "@/app/services/all/lending/demand";

export async function createLoanDemand(data: {
  loan: string;
  demand_type: "Penalty" | "Charges";
  amount: number;
  date: string;
  description?: string; // Mapped to demand_subtype usually or remarks
}) {
  if (!(await verifyLendingRole()))
    return { success: false, error: "Unauthorized" };

  try {
    const message = await DemandService.create(data);
    return { success: true, message: `Demand Raised (${message.name})` };
  } catch (e: any) {
    console.error("Demand Creation Failed", e);
    return { success: false, error: e.message || "Failed to raise demand" };
  }
}
