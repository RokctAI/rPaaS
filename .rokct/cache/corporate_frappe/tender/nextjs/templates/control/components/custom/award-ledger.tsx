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
  type AwardLedger,
  type AwardLedgerMatch,
} from "@/app/services/control/bids";

// Award-outcome ledger (plan #12, deterministic - no AI): the user's OWN
// outcome record plus published-award matches for their claimed ocids.
// Server component - renders nothing when the user has no outcome-bearing
// bids and no matches (or on any control-plane hiccup: the bids page must
// never break on this section). Honesty rules mirrored from the backend:
// win rate is a record over decided bids, never a probability; "no award
// published" is NEVER shown as lost; the caveats render with the numbers.

const MAX_MATCH_ROWS = 8;

function formatRand(value: number | null | undefined): string | null {
  if (value == null || Number.isNaN(value)) return null;
  const abs = Math.abs(value);
  if (abs >= 1e9) return `R${(value / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `R${(value / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `R${Math.round(value / 1e3)}k`;
  return `R${Math.round(value)}`;
}

function matchLine(match: AwardLedgerMatch): string {
  if (!match.published_award) return match.note;
  const award = match.awards[0];
  if (!award) return match.note;
  const winner =
    award.winner && !award.winner_placeholder
      ? award.winner
      : "(placeholder supplier string in the published record)";
  const value = award.value_usable ? formatRand(award.value_rand) : null;
  const valuePart = value
    ? ` at ${value}`
    : ` (no usable published amount${award.amount_flag ? `: ${award.amount_flag}` : ""})`;
  const datePart = award.date_proxy
    ? ` - release dated ${award.date_proxy.slice(0, 10)} (no award dates on this feed)`
    : "";
  return `Published winner: ${winner}${valuePart}${datePart}`;
}

export async function AwardLedgerSection() {
  let ledger: AwardLedger | null = null;
  try {
    ledger = await TenderBidService.getAwardLedger();
  } catch {
    return null;
  }
  if (!ledger?.own_outcomes || !ledger?.published_matches) return null;

  const own = ledger.own_outcomes;
  const matches = (ledger.published_matches.matches || []).filter(
    (m) => m.ocid && m.release_cached,
  );
  const hasOwnRecord = own.decided > 0 || own.awaiting_outcome > 0;
  if (!hasOwnRecord && matches.length === 0) return null;

  const shown = matches.slice(0, MAX_MATCH_ROWS);
  const more = matches.length - shown.length;

  return (
    <section className="mt-12">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
          Award ledger
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Your own outcome record, plus what the public award feed published
          for your claimed tenders. A record and market context — never a win
          probability.
        </p>
      </div>

      {hasOwnRecord && (
        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 mb-3">
          <p className="text-sm font-semibold text-zinc-900 dark:text-white">
            Your record (private to you)
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
            <span>{own.tracked} tracked</span>
            <span>{own.awaiting_outcome} submitted, awaiting outcome</span>
            {own.win_rate ? (
              <span>
                {own.win_rate.awarded} of {own.win_rate.decided} decided bids
                awarded ({own.win_rate.rate_pct}% of your decided bids — a
                record, not a probability)
              </span>
            ) : (
              <span>no decided outcomes yet — no rate is computed over zero</span>
            )}
          </div>
          {own.quoted_vs_awarded.length > 0 && (
            <div className="mt-3 flex flex-col gap-1">
              {own.quoted_vs_awarded.map((row) => (
                <p
                  key={row.bid}
                  className="text-xs text-zinc-600 dark:text-zinc-400"
                >
                  <span className="font-medium text-zinc-900 dark:text-zinc-200">
                    {row.tender_title || row.tender_slug}:
                  </span>{" "}
                  quoted {formatRand(row.quoted_rand) ?? "—"}, awarded{" "}
                  {formatRand(row.awarded_rand) ?? "—"}
                  {row.delta_pct != null && <> ({row.delta_pct > 0 ? "+" : ""}{row.delta_pct}%)</>}
                  {row.awarded_band_position?.position && (
                    <> — {row.awarded_band_position.position.replace(/_/g, " ")} of the band shown at bid time</>
                  )}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {shown.length > 0 && (
        <div className="flex flex-col gap-3">
          {shown.map((match) => (
            <div
              key={match.bid}
              className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-zinc-900 dark:text-white">
                    {match.tender_title || match.tender_slug}
                  </p>
                  {match.institution && (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                      {match.institution}
                    </p>
                  )}
                </div>
                <span className="shrink-0 rounded-full border border-zinc-200 dark:border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-600 dark:text-zinc-300">
                  {match.published_award ? "award published" : "no award published"}
                </span>
              </div>
              <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
                {matchLine(match)}
              </p>
            </div>
          ))}
        </div>
      )}

      {more > 0 && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          + {more} more matched releases.
        </p>
      )}

      {ledger.caveats?.length > 0 && (
        <ul className="mt-4 flex flex-col gap-1">
          {ledger.caveats.map((caveat, i) => (
            <li
              key={i}
              className="text-[11px] leading-snug text-zinc-500 dark:text-zinc-500"
            >
              {caveat}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
