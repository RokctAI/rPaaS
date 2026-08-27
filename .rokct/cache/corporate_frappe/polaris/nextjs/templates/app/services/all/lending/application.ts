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

export class ApplicationService {
  static async getList(page = 1, limit = 20, options?: ServiceOptions) {
    const start = (page - 1) * limit;
    const response = await BaseService.call(
      "frappe.client.get_list",
      {
        doctype: "Loan Application",
        fields: [
          "name",
          "applicant",
          "applicant_type",
          "loan_amount",
          "status",
          "loan_product",
          "posting_date",
          "rate_of_interest",
          "workflow_state",
          "owner",
          "risk_level",
        ],
        limit_start: start,
        limit_page_length: limit,
        order_by: "creation desc",
      },
      options,
    );

    const countRes = await BaseService.call(
      "frappe.client.get_value",
      {
        doctype: "Loan Application",
        filters: {},
        fieldname: "count(name) as total",
      },
      options,
    );

    return {
      data: response?.message || [],
      total: countRes?.message?.total || 0,
      page,
      limit,
    };
  }

  static async get(id: string, options?: ServiceOptions) {
    const response = await BaseService.call(
      "frappe.client.get",
      {
        doctype: "Loan Application",
        name: id,
      },
      options,
    );
    return response?.message;
  }

  static async create(data: any, options?: ServiceOptions) {
    const response = await BaseService.call(
      "frappe.client.insert",
      {
        doc: { doctype: "Loan Application", ...data },
      },
      options,
    );
    return response?.message;
  }

  static async update(name: string, data: any, options?: ServiceOptions) {
    const response = await BaseService.call(
      "frappe.client.set_value",
      {
        doctype: "Loan Application",
        name: name,
        fieldname: data,
      },
      options,
    );
    return response?.message;
  }
}
