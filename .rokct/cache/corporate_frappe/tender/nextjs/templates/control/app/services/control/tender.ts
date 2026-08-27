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

import { ControlBaseService } from "./base";

// Admin service for the tender doctypes. Queries here are aligned to the REAL
// doctype schemas (tender SDK, corporate/tender/frappe/doctype/):
//
// - Tender Control Settings is a SINGLE doctype (fields: tender_country,
//   enforce_submission_gates) - read via frappe.client.get, never get_list.
// - Tender Workflow Task and Generated Tender Task are CHILD TABLES
//   (istable=1; fields: subject, due_date_offset_days). Frappe blocks bare
//   get_list and direct insert/update/delete on child tables, so rows are
//   read and mutated through their parents (Tender Workflow Template.tasks
//   and Intelligent Task Set.tasks) via frappe.client.save.
// - Tender Workflow Template fields: template_name, tasks (creator is the
//   standard `owner` field - `created_by` never existed).
// - Intelligent Task Set fields: ocid, tasks (set_name/description never
//   existed).

export interface WorkflowTaskRow {
  name: string;
  parent: string;
  subject: string;
  due_date_offset_days: number;
}

export class TenderService {
  private static async saveDoc(doc: any) {
    const response = await ControlBaseService.call("frappe.client.save", { doc });
    return response?.message;
  }

  // ── Tender Control Settings (Single) ────────────────────────────────────

  static async getTenderControlSettings() {
    return ControlBaseService.getDoc("Tender Control Settings", "Tender Control Settings");
  }

  static async updateTenderControlSettings(data: any) {
    return ControlBaseService.update("Tender Control Settings", "Tender Control Settings", data);
  }

  // ── Tender Workflow Template (parent) + Tender Workflow Task (child) ────

  static async getTenderWorkflowTemplates() {
    return ControlBaseService.getList("Tender Workflow Template", {
      fields: ["name", "template_name", "owner"],
      order_by: "modified desc",
    });
  }

  static async getTenderWorkflowTasks(): Promise<WorkflowTaskRow[]> {
    const templates = await this.getTenderWorkflowTemplates();
    const docs = await Promise.all(
      (templates ?? []).map((t: any) =>
        ControlBaseService.getDoc("Tender Workflow Template", t.name),
      ),
    );
    return docs.flatMap((doc: any) =>
      (doc?.tasks ?? []).map((row: any) => ({
        name: row.name,
        parent: doc.name,
        subject: row.subject,
        due_date_offset_days: row.due_date_offset_days,
      })),
    );
  }

  static async createTenderWorkflowTemplate(data: any) {
    return ControlBaseService.insert({
      doctype: "Tender Workflow Template",
      ...data,
    });
  }

  static async updateTenderWorkflowTemplate(name: string, data: any) {
    return ControlBaseService.update("Tender Workflow Template", name, data);
  }

  static async deleteTenderWorkflowTemplate(name: string) {
    return ControlBaseService.delete("Tender Workflow Template", name);
  }

  static async createTenderWorkflowTask(
    template: string,
    data: { subject: string; due_date_offset_days: number },
  ) {
    const doc = await ControlBaseService.getDoc("Tender Workflow Template", template);
    doc.tasks = [...(doc.tasks ?? []), data];
    return this.saveDoc(doc);
  }

  static async updateTenderWorkflowTask(template: string, rowName: string, data: any) {
    const doc = await ControlBaseService.getDoc("Tender Workflow Template", template);
    doc.tasks = (doc.tasks ?? []).map((row: any) =>
      row.name === rowName ? { ...row, ...data } : row,
    );
    return this.saveDoc(doc);
  }

  static async deleteTenderWorkflowTask(template: string, rowName: string) {
    const doc = await ControlBaseService.getDoc("Tender Workflow Template", template);
    doc.tasks = (doc.tasks ?? []).filter((row: any) => row.name !== rowName);
    return this.saveDoc(doc);
  }

  // ── Intelligent Task Set (parent) + Generated Tender Task (child) ───────

  static async getIntelligentTaskSets() {
    return ControlBaseService.getList("Intelligent Task Set", {
      fields: ["name", "ocid"],
      order_by: "modified desc",
    });
  }

  static async getGeneratedTenderTasks(): Promise<(WorkflowTaskRow & { ocid: string })[]> {
    const sets = await this.getIntelligentTaskSets();
    const docs = await Promise.all(
      (sets ?? []).map((s: any) => ControlBaseService.getDoc("Intelligent Task Set", s.name)),
    );
    return docs.flatMap((doc: any) =>
      (doc?.tasks ?? []).map((row: any) => ({
        name: row.name,
        parent: doc.name,
        ocid: doc.ocid,
        subject: row.subject,
        due_date_offset_days: row.due_date_offset_days,
      })),
    );
  }

  static async createIntelligentTaskSet(data: any) {
    return ControlBaseService.insert({
      doctype: "Intelligent Task Set",
      ...data,
    });
  }

  static async updateIntelligentTaskSet(name: string, data: any) {
    return ControlBaseService.update("Intelligent Task Set", name, data);
  }

  static async deleteIntelligentTaskSet(name: string) {
    return ControlBaseService.delete("Intelligent Task Set", name);
  }

  static async createGeneratedTenderTask(
    taskSet: string,
    data: { subject: string; due_date_offset_days: number },
  ) {
    const doc = await ControlBaseService.getDoc("Intelligent Task Set", taskSet);
    doc.tasks = [...(doc.tasks ?? []), data];
    return this.saveDoc(doc);
  }

  static async updateGeneratedTenderTask(taskSet: string, rowName: string, data: any) {
    const doc = await ControlBaseService.getDoc("Intelligent Task Set", taskSet);
    doc.tasks = (doc.tasks ?? []).map((row: any) =>
      row.name === rowName ? { ...row, ...data } : row,
    );
    return this.saveDoc(doc);
  }

  static async deleteGeneratedTenderTask(taskSet: string, rowName: string) {
    const doc = await ControlBaseService.getDoc("Intelligent Task Set", taskSet);
    doc.tasks = (doc.tasks ?? []).filter((row: any) => row.name !== rowName);
    return this.saveDoc(doc);
  }
}
