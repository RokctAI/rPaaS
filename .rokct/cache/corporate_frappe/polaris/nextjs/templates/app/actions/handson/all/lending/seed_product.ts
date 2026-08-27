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
import { ProductService } from "@/app/services/all/lending/product";

export async function createDefaultUnsecuredProduct() {
  if (!(await verifyLendingRole()))
    return { success: false, message: "Unauthorized" };

  try {
    await ProductService.create({
      item_code: "Unsecured Personal Loan",
      product_name: "Unsecured Personal Loan",
      rate_of_interest: 28, // Just under the 29% cap
      currency: "ZAR",
      is_term_loan: 1,
      repayment_method: "Repay Fixed Amount per Period",
    });

    revalidatePath("/handson/all/lending/product");
    return {
      success: true,
      message: "Unsecured Personal Loan created successfully.",
    };
  } catch (e: any) {
    if (e.message === "Product already exists.") {
      return { success: false, message: e.message };
    }
    console.error(e);
    return { success: false, message: "Failed to create product." };
  }
}

export async function createDefaultShortTermProduct() {
  if (!(await verifyLendingRole()))
    return { success: false, message: "Unauthorized" };

  try {
    await ProductService.create({
      item_code: "1-Month Micro Loan",
      product_name: "1-Month Micro Loan",
      rate_of_interest: 60, // 5% per month * 12
      currency: "ZAR",
      is_term_loan: 1,
      repayment_method: "Repay Fixed Amount per Period",
    });

    revalidatePath("/handson/all/lending/product");
    return { success: true, message: "Short Term Loan created successfully." };
  } catch (e: any) {
    if (e.message === "Product already exists.") {
      return { success: false, message: e.message };
    }
    console.error(e);
    return { success: false, message: "Failed to create product." };
  }
}

export async function createDefaultPawnProduct() {
  if (!(await verifyLendingRole()))
    return { success: false, message: "Unauthorized" };

  try {
    await ProductService.create({
      item_code: "Secured Pawn Loan",
      product_name: "Secured Pawn Loan",
      rate_of_interest: 60, // Short Term Pawn Cap
      currency: "ZAR",
      is_term_loan: 1,
      is_secured_loan: 1, // Crucial for Pawn
      repayment_method: "Repay Fixed Amount per Period",
    });

    revalidatePath("/handson/all/lending/product");
    return { success: true, message: "Pawn Loan created successfully." };
  } catch (e: any) {
    if (e.message === "Product already exists.") {
      return { success: false, message: e.message };
    }
    console.error(e);
    return { success: false, message: "Failed to create product." };
  }
}
