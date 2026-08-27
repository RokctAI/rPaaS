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

export class TransferService {
  static async create(
    data: {
      transfer_date: string;
      from_branch: string;
      to_branch: string;
      loans: string[];
      company: string;
      applicant?: string;
    },
    options?: ServiceOptions,
  ) {
    const doc = {
      doctype: "Loan Transfer",
      transfer_date: data.transfer_date,
      company: data.company,
      from_branch: data.from_branch,
      to_branch: data.to_branch,
      applicant: data.applicant,
      loans: data.loans.map((loanId) => ({ loan: loanId })),
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

  static async getLoansByBranch(
    branch: string,
    applicant?: string,
    options?: ServiceOptions,
  ) {
    const filters: any = { branch: branch, docstatus: 1, status: "Active" };
    if (applicant) filters.applicant = applicant;

    const response = await BaseService.call(
      "frappe.client.get_list",
      {
        doctype: "Loan",
        filters: filters,
        fields: ["name", "applicant_name", "loan_amount", "outstanding_amount"],
      },
      options,
    );

    return response?.message || [];
  }

  static async getBranches(options?: ServiceOptions) {
    const response = await BaseService.call(
      "frappe.client.get_list",
      {
        doctype: "Branch",
        fields: ["name"],
      },
      options,
    );
    return response?.message || [];
  }
}
