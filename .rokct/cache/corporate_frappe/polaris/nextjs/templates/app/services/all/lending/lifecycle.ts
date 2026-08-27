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

export class LifecycleService {
  static async createLoanWriteOff(
    loan: string,
    amount: number,
    options?: ServiceOptions,
  ) {
    const doc = {
      doctype: "Loan Write Off",
      loan: loan,
      write_off_amount: amount,
      posting_date: new Date().toISOString().split("T")[0],
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

  static async createLoanRestructure(
    data: {
      loan: string;
      date: string;
      reason?: string;
      new_term_months?: number;
      new_interest_rate?: number;
    },
    options?: ServiceOptions,
  ) {
    const doc: any = {
      doctype: "Loan Restructure",
      loan: data.loan,
      restructure_type: "Normal Restructure",
      restructure_date: data.date,
      reason_for_restructure: data.reason,
      status: "Initiated",
    };
    if (data.new_term_months)
      doc.new_repayment_period_in_months = data.new_term_months;
    if (data.new_interest_rate)
      doc.new_rate_of_interest = data.new_interest_rate;

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

  static async createBalanceAdjustment(
    data: {
      loan: string;
      amount: number;
      type: "Debit Adjustment" | "Credit Adjustment";
      remarks?: string;
    },
    options?: ServiceOptions,
  ) {
    const doc = {
      doctype: "Loan Balance Adjustment",
      loan: data.loan,
      adjustment_type: data.type,
      amount: data.amount,
      posting_date: new Date().toISOString().split("T")[0],
      remarks: data.remarks,
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
