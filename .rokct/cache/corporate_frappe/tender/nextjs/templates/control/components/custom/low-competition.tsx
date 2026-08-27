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

import Link from "next/link";

import {
  TenderBidService,
  type LowCompetitionOpportunity,
  type NarrownessTier,
} from "@/app/services/control/bids";

// Low-competition finder (deterministic - no AI): live tenders whose FIELD
// of qualifying firms is narrow, computed from public requirements only
// (required CIDB grade, EME/QSE set-asides, B-BBEE prequalification,
// compulsory briefings, short windows, local content), and whose narrowing
// requirements the caller's business profile actually clears. It describes
// the field, never a win probability. Server component - renders nothing at
// all when the finder is empty or unavailable (a control plane hiccup or a
// missing business profile must never break the page).

const MAX_ROWS = 6;

const TIER_LABEL: Record<NarrownessTier, string> = {
  wide: "wide field",
  moderate: "moderate field",
  narrow: "narrow field",
  very_narrow: "very narrow field",
};

function formatDate(value?: string): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

function tierBadge(entry: LowCompetitionOpportunity): string {
  return TIER_LABEL[entry.narrowness.tier] ?? entry.narrowness.tier;
}

export async function LowCompetitionSection() {
  let opportunities: LowCompetitionOpportunity[] = [];
  try {
    const radar = await TenderBidService.getLowCompetitionTenders();
    opportunities = Array.isArray(radar?.opportunities)
      ? radar.opportunities
      : [];
  } catch {
    return null;
  }
  if (opportunities.length === 0) return null;

  const shown = opportunities.slice(0, MAX_ROWS);
  const more = opportunities.length - shown.length;

  return (
    <section className="mt-12">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
          Low-competition finder
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Live tenders where the public requirements narrow the field of firms
          that can even bid — and your profile clears them. Field narrowness
          only, never a win prediction.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {shown.map((entry) => (
          <div
            key={entry.slug ?? entry.title}
            className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                {entry.slug ? (
                  <Link
                    href={`/opportunities/tenders/${entry.slug}`}
                    className="text-sm font-semibold text-zinc-900 dark:text-white hover:text-purple-600 dark:hover:text-purple-400 transition-colors line-clamp-2"
                  >
                    {entry.title || entry.slug}
                  </Link>
                ) : (
                  <p className="text-sm font-semibold text-zinc-900 dark:text-white line-clamp-2">
                    {entry.title}
                  </p>
                )}
                {entry.institution && (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {entry.institution}
                  </p>
                )}
              </div>
              <span className="shrink-0 rounded-full border border-zinc-200 dark:border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-600 dark:text-zinc-300">
                {tierBadge(entry)} · {entry.narrowness.score}/100
              </span>
            </div>
            {entry.narrowness.signals.length > 0 && (
              <ul className="mt-2 flex flex-col gap-1">
                {entry.narrowness.signals.map((signal) => (
                  <li
                    key={signal.code}
                    className="text-xs text-zinc-600 dark:text-zinc-400"
                  >
                    {signal.detail}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
              <span>
                Closes:{" "}
                <span className="font-medium text-zinc-900 dark:text-zinc-200">
                  {formatDate(entry.closing_date)}
                </span>
              </span>
              {typeof entry.days_to_close === "number" && (
                <span>{entry.days_to_close} day(s) left</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {more > 0 && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          + {more} more narrow-field tenders your profile clears.
        </p>
      )}
    </section>
  );
}
