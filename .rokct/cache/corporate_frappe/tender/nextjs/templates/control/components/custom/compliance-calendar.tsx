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
  type ComplianceCalendarEntry,
} from "@/app/services/control/bids";

// Unified compliance calendar (assessment plan #13): the four date streams
// (bid closings, briefings, artifact expiries, renewal windows) merged into
// one upcoming feed - the bid desk's operating rhythm. Server component -
// renders NOTHING when the calendar is empty or unavailable (a control-plane
// hiccup must never break the bids page). Honesty rule enforced in the
// rendering itself: renewal_window entries are WATCH items - they get a
// distinct watch badge and window wording, never deadline styling.

const MAX_ROWS = 12;

const STREAM_LABEL: Record<ComplianceCalendarEntry["stream"], string> = {
  bid_closing: "Bid closes",
  briefing: "Briefing",
  artifact_expiry: "Document expires",
  renewal_window: "Expected re-advert",
};

function daysLabel(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

export async function ComplianceCalendarSection() {
  let entries: ComplianceCalendarEntry[] = [];
  let total = 0;
  try {
    const calendar = await TenderBidService.getComplianceCalendar();
    entries = Array.isArray(calendar?.entries) ? calendar.entries : [];
    total = calendar?.summary?.total ?? entries.length;
  } catch {
    return null;
  }
  if (entries.length === 0) return null;

  const shown = entries.slice(0, MAX_ROWS);
  const more = total - shown.length;
  const hasWatchRows = shown.some((e) => e.item_class === "watch");

  return (
    <section className="mt-12">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
          Upcoming compliance calendar
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Bid closings, briefings and expiring documents on one clock — plus
          predicted re-advert windows as watch items, never deadlines.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        {shown.map((entry) => {
          const isWatch = entry.item_class === "watch";
          return (
            <div
              key={`${entry.stream}-${entry.ref.name}-${entry.date}`}
              className={
                "rounded-xl border p-3 flex flex-wrap items-start gap-x-4 gap-y-1 " +
                (isWatch
                  ? "border-dashed border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/60"
                  : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900")
              }
            >
              <div className="shrink-0 w-28">
                <p className="text-sm font-semibold text-zinc-900 dark:text-white">
                  {entry.date}
                </p>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                  {daysLabel(entry.days_away)}
                </p>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[11px] border " +
                      (isWatch
                        ? "border-zinc-300 dark:border-zinc-600 text-zinc-500 dark:text-zinc-400"
                        : "border-purple-200 dark:border-purple-900/50 text-purple-700 dark:text-purple-300")
                    }
                  >
                    {STREAM_LABEL[entry.stream] ?? entry.stream}
                  </span>
                  {isWatch && (
                    <span className="rounded-full bg-zinc-200 dark:bg-zinc-800 px-2 py-0.5 text-[11px] text-zinc-600 dark:text-zinc-300">
                      watch — not a commitment
                    </span>
                  )}
                  <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 line-clamp-1">
                    {entry.title}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-2">
                  {isWatch &&
                  entry.ref.predicted_window_start &&
                  entry.ref.predicted_window_end
                    ? `Window ${entry.ref.predicted_window_start} – ${entry.ref.predicted_window_end} — ${entry.detail}`
                    : entry.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {more > 0 && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          + {more} more dated items inside the 90-day horizon.
        </p>
      )}

      {hasWatchRows && (
        <p className="mt-3 text-[11px] text-zinc-400 dark:text-zinc-500">
          Predicted re-advert windows are deterministic lead-calendar entries
          from the renewal ledger — only 2 of 12 sampled due predictions
          validated as unambiguous same-service returns, so treat them as
          prompts to prepare, never as dates a tender will appear.
        </p>
      )}
    </section>
  );
}
