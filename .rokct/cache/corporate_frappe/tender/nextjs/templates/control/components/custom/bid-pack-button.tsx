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

"use client";

import { useState } from "react";

import { createBidQuotation, generateBidPack } from "@/app/actions/opportunities/bids";

// Two-step bid-pack flow: "Bid pack" generates the UNSIGNED review copy
// (signature/initials slots render as "Sign here" / "Initial here" markers);
// once reviewed, "Sign & initial" regenerates with the profile's stamped
// signature images. The pack opens in a new tab as printable HTML - the
// browser's print dialog produces the PDF.
export function BidPackButton({ bidName }: { bidName: string }) {
  const [busy, setBusy] = useState<"review" | "sign" | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(sign: boolean) {
    setBusy(sign ? "sign" : "review");
    setError(null);
    try {
      const res = await generateBidPack(bidName, sign);
      if (!res || "error" in res) {
        setError((res as { error?: string })?.error || "Unable to generate bid pack");
        return;
      }
      const blob = new Blob([res.html], { type: "text/html" });
      window.open(URL.createObjectURL(blob), "_blank", "noopener");
      if (!sign) setReviewed(true);
      const gates = res.manifest?.open_fatal_gates?.length ?? 0;
      if (gates > 0) {
        setError(
          `${gates} fatal compliance gate${gates === 1 ? "" : "s"} still open - see the pack's warning page.`,
        );
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => run(false)}
          disabled={busy !== null}
          className="rounded-lg border border-purple-600 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 text-xs font-medium px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {busy === "review" ? "Generating…" : "Bid pack"}
        </button>
        {reviewed && (
          <button
            type="button"
            onClick={() => run(true)}
            disabled={busy !== null}
            className="rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium px-3 py-1.5 transition-colors disabled:opacity-50"
          >
            {busy === "sign" ? "Signing…" : "Sign & initial"}
          </button>
        )}
      </div>
      {error && (
        <p className="text-xs text-red-600 dark:text-red-400 max-w-[240px] text-right">{error}</p>
      )}
    </div>
  );
}

// Soft erp integration: creates a draft Quotation linked to the bid so the
// user prices line items in ERP and the pack's pricing schedule fills from
// them. On sites without the erp module the backend returns a clear error
// and the pricing schedule stays a fill-by-hand section - by design.
export function CreateQuotationButton({ bidName }: { bidName: string }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await createBidQuotation(bidName);
      if (!res || "error" in res) {
        setError((res as { error?: string })?.error || "Unable to create a quotation");
        return;
      }
      setResult(
        res.created
          ? `Draft quotation ${res.quotation} created - price it in ERP.`
          : `Quotation ${res.quotation} already linked.`,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={run}
        disabled={busy}
        className="rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-xs font-medium px-3 py-1.5 transition-colors disabled:opacity-50"
      >
        {busy ? "Creating…" : "Create quotation"}
      </button>
      {result && <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-[240px] text-right">{result}</p>}
      {error && <p className="text-xs text-red-600 dark:text-red-400 max-w-[240px] text-right">{error}</p>}
    </div>
  );
}
