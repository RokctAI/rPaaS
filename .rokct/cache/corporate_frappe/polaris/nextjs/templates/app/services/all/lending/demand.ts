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

import { BaseService, ServiceOptions } from "@/app/services/common/base";

export class DemandService {
  static async create(
    data: {
      loan: string;
      demand_type: "Penalty" | "Charges";
      amount: number;
      date: string;
      description?: string;
    },
    options?: ServiceOptions,
  ) {
    // Fetch Loan first to get context, similar to original logic
    const loanDoc = await BaseService.call(
      "frappe.client.get",
      {
        doctype: "Loan",
        name: data.loan,
      },
      options,
    );

    if (!loanDoc?.message) throw new Error("Loan not found");
    const loan = loanDoc.message;

    const doc = {
      doctype: "Loan Demand",
      loan: data.loan,
      demand_type: data.demand_type,
      demand_subtype:
        data.demand_type === "Penalty" ? "Penalty" : "Miscellaneous",
      demand_date: data.date,
      posting_date: data.date,
      demand_amount: data.amount,
      company: loan.company,
      applicant_type: loan.applicant_type,
      applicant: loan.applicant,
      loan_product: loan.loan_product,
    };

    const res = await BaseService.call(
      "frappe.client.insert",
      { doc: doc },
      options,
    );
    if (res?.message) {
      await BaseService.call(
        "frappe.client.submit",
        { doc: res.message },
        options,
      );
    }

    return res?.message;
  }
}
