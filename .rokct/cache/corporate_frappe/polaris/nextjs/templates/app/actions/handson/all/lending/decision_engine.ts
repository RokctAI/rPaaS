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
import { revalidatePath } from "next/cache";
import { DecisionService } from "@/app/services/all/lending/decision";

export async function runDecisionEngine(applicationId: string) {
  if (!applicationId)
    return { success: false, message: "Application ID is required" };

  // Auth Check
  if (!(await verifyLendingRole()))
    return { success: false, message: "Unauthorized" };

  try {
    const data = await DecisionService.runEngine(applicationId);
    revalidatePath(`/handson/all/lending/application/${applicationId}`);
    return { success: true, data: data };
  } catch (e: any) {
    console.error("Decision Engine Failed:", e);
    return {
      success: false,
      message: e?.message || "Failed to run decision engine",
    };
  }
}
