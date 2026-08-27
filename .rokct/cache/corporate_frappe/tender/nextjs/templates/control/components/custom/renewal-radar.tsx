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

import {
  TenderBidService,
  type RenewalWatchEntry,
} from "@/app/services/control/bids";

// Renewal radar (Ray's ledger design, deterministic - no AI): contracts the
// ledger predicts will come back for re-advertisement. A lead calendar, not
// a certainty: the row says "prepare now", and the successor is matched by
// buyer + category when it actually appears. Server component - renders
// nothing at all when the radar is empty or unavailable (a control plane
// hiccup must never break the bids page).

const MAX_ROWS = 8;

function formatDate(value: string | null): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

function sourceLabel(entry: RenewalWatchEntry): string {
  if (entry.source === "stated_duration") {
    return entry.stated_duration_months
      ? `stated ${entry.stated_duration_months}-month term`
      : "stated term";
  }
  return "observed cycle";
}

export async function RenewalRadarSection() {
  let watches: RenewalWatchEntry[] = [];
  let openTotal = 0;
  try {
    const radar = await TenderBidService.getRenewalRadar();
    watches = Array.isArray(radar?.watches) ? radar.watches : [];
    openTotal = radar?.summary?.open_total ?? watches.length;
  } catch {
    return null;
  }
  if (watches.length === 0) return null;

  const shown = watches.slice(0, MAX_ROWS);
  const more = watches.length - shown.length;

  return (
    <section className="mt-12">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
          Renewal radar
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Contracts predicted to come back for re-advertisement — get
          registrations and documents ready before the advert appears. A lead
          calendar, not a certainty.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {shown.map((entry) => (
          <div
            key={entry.name}
            className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-zinc-900 dark:text-white">
                  {entry.buyer}
                </p>
                {entry.category && (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {entry.category}
                  </p>
                )}
              </div>
              <span className="shrink-0 rounded-full border border-zinc-200 dark:border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-600 dark:text-zinc-300">
                {sourceLabel(entry)}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
              <span>
                Expected window:{" "}
                <span className="font-medium text-zinc-900 dark:text-zinc-200">
                  {formatDate(entry.predicted_window_start)} –{" "}
                  {formatDate(entry.predicted_window_end)}
                </span>
              </span>
              {entry.trust && entry.trust.resolved > 0 && (
                <span>
                  Buyer track record: {entry.trust.confirmed} of{" "}
                  {entry.trust.resolved} predictions confirmed
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {more > 0 && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          + {more} more predicted re-adverts on the radar ({openTotal} open
          watches in total).
        </p>
      )}
    </section>
  );
}
