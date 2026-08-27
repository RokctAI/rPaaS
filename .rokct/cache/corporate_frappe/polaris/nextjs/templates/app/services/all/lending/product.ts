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

export class ProductService {
  static async getList(options?: ServiceOptions) {
    // Using existing backend method
    const response = await BaseService.call(
      "core.polaris.tenant.api.product.get_loan_product_list",
      {},
      options,
    );
    return response?.message || [];
  }

  static async get(name: string, options?: ServiceOptions) {
    const response = await BaseService.call(
      "frappe.client.get",
      {
        doctype: "Loan Product",
        name: name,
      },
      options,
    );
    return response?.message;
  }

  static async create(data: any, options?: ServiceOptions) {
    // Create logic for seed product
    // Check existence
    const existing = await BaseService.call(
      "frappe.client.get_value",
      {
        doctype: "Loan Product",
        filters: { product_name: data.product_name },
        fieldname: "name",
      },
      options,
    );

    if (existing?.message?.name) {
      throw new Error("Product already exists.");
    }

    const response = await BaseService.call(
      "frappe.client.insert",
      {
        doc: { doctype: "Loan Product", ...data },
      },
      options,
    );
    return response?.message;
  }

  static async isControlSite(options?: ServiceOptions) {
    const response = await BaseService.call(
      "control.utils.is_control_site",
      {},
      options,
    );
    return response?.message === true;
  }
}
