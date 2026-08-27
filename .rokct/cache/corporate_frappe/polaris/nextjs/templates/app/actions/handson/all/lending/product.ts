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
import { ProductService } from "@/app/services/all/lending/product";

export async function getLoanProducts() {
  // Note: Returns empty array on failure, handled by UI generic loading/empty state.
  // Ideally refactor to return { data, error } pattern later.
  if (!(await verifyLendingRole())) return [];

  try {
    return await ProductService.getList();
  } catch (e) {
    console.error("Failed to fetch Loan Products", e);
    return [];
  }
}

export async function getLoanProduct(name: string) {
  if (!(await verifyLendingRole())) return null;

  try {
    return await ProductService.get(name);
  } catch (e) {
    return null;
  }
}
