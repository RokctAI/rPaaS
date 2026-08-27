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

import type { BidPricingBand } from "@/app/services/control/bids";

// Bid-time pricing band: the typical winning-price band (median + IQR of
// published eTenders award amounts) for the bid's buyer / category /
// province, resolved server-side down the market-context fallback chain
// and attached to the get_my_bids payload. Presentational only - all
// selection and formatting already happened in the frappe-free
// compliance/pricing_bands.py module. Renders NOTHING when the bid
// carries no band (renewal-radar.tsx doctrine: a missing benchmark must
// never break or clutter the bids page - absence is honest, not an
// error state).

export function PricingBandPanel({ band }: { band?: BidPricingBand | null }) {
  if (!band || band.median_rand == null || !band.median_label) return null;

  return (
    <div className="mt-3 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 px-3 py-2">
      <p className="text-xs text-zinc-600 dark:text-zinc-300">
        <span className="font-medium text-zinc-800 dark:text-zinc-200">
          {band.scope}:
        </span>{" "}
        median{" "}
        <span className="font-semibold text-zinc-900 dark:text-white">
          {band.median_label}
        </span>
        {band.iqr_label && <>, middle half {band.iqr_label}</>}
        {band.n != null && (
          <span className="text-zinc-400 dark:text-zinc-500">
            {" "}
            · {band.n.toLocaleString()} published awards
            {band.dataset?.snapshot_date && ` · snapshot ${band.dataset.snapshot_date}`}
          </span>
        )}
      </p>
      <p className="mt-1 text-[11px] leading-snug text-zinc-400 dark:text-zinc-500">
        {band.caveat}
      </p>
    </div>
  );
}
