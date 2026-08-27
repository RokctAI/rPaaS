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
  type BuyerDossier,
} from "@/app/services/control/bids";

// Buyer dossier panel: per-buyer behavioural stats from the published
// eTenders award record (control:get_buyer_dossier) - award volume,
// typical award value (median/IQR, N-gated), supplier concentration over
// identified awards, and the newcomer-openness proxy. Everything was
// computed deterministically at build time from the committed public
// dataset; this panel only displays it. Server component - renders
// nothing at all when the buyer is unmatched, the call fails, or the
// viewer is not logged in (a control plane hiccup must never break the
// detail page). Renewal-radar doctrine: honest caveats stay visible.

function formatRand(amount: number | null | undefined): string {
  if (amount == null || isNaN(amount)) return "—";
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `R${(amount / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `R${(amount / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `R${Math.round(amount / 1e3)}k`;
  return `R${Math.round(amount)}`;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
        {label}
      </span>
      <span className="text-sm text-zinc-800 dark:text-zinc-200">{value}</span>
    </div>
  );
}

export async function BuyerDossierPanel({ buyer }: { buyer: string }) {
  if (!buyer) return null;

  let payload: BuyerDossier | null = null;
  try {
    payload = await TenderBidService.getBuyerDossier(buyer);
  } catch {
    return null;
  }
  const dossier = payload?.available && payload.matched ? payload.dossier : null;
  if (!dossier || !dossier.award_count) return null;

  const hasBand = dossier.median_rand != null;
  const hasConcentration = dossier.top_supplier_share_pct != null;
  const hasNewcomer = dossier.single_win_supplier_share_pct != null;

  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 p-5 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wide">
          Buyer dossier
        </h2>
        <span className="text-xs text-zinc-400">
          {dossier.award_count.toLocaleString()} published award
          {dossier.award_count === 1 ? "" : "s"}
          {payload?.dataset?.snapshot_date
            ? ` · snapshot ${payload.dataset.snapshot_date}`
            : ""}
        </span>
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
        How {dossier.buyer} behaves in the published eTenders award record —
        aggregate public data, not a prediction.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat
          label="Typical award value"
          value={
            hasBand
              ? `${formatRand(dossier.median_rand)} median`
              : "too few published amounts"
          }
        />
        <Stat
          label="Middle half of awards"
          value={
            hasBand && dossier.iqr_rand
              ? `${formatRand(dossier.iqr_rand[0])} – ${formatRand(dossier.iqr_rand[1])}`
              : "—"
          }
        />
        <Stat
          label="Supplier spread"
          value={
            hasConcentration && dossier.distinct_supplier_count != null
              ? `${dossier.distinct_supplier_count.toLocaleString()} suppliers · top wins ${dossier.top_supplier_share_pct}%`
              : "too few identified awards"
          }
        />
        <Stat
          label="One-time winners"
          value={
            hasNewcomer
              ? `${dossier.single_win_supplier_share_pct}% of identified awards`
              : "too few identified awards"
          }
        />
      </div>

      {hasNewcomer && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400 leading-snug">
          {dossier.single_win_supplier_share_pct}% of this buyer&apos;s
          identified published awards went to suppliers appearing only once
          for it — a rough openness-to-newcomers signal within the published
          record, not a measured entry rate.
        </p>
      )}

      {payload?.renewal && payload.renewal.trust.resolved > 0 && (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400 leading-snug">
          Renewal track record: {payload.renewal.trust.confirmed} of{" "}
          {payload.renewal.trust.resolved} predicted re-advertisements
          confirmed
          {payload.renewal.lateness_days != null &&
            ` · typically re-advertises about ${Math.abs(payload.renewal.lateness_days)} days ${payload.renewal.lateness_days >= 0 ? "late" : "early"} against stated durations`}
          . Counts from the renewal ledger, never probabilities.
        </p>
      )}

      <p className="mt-3 text-[11px] leading-snug text-zinc-400 dark:text-zinc-500">
        Published award records only (winners, no losing bids), with heavy
        per-buyer publication bias; supplier stats exclude the ~38% of rows
        carrying a placeholder supplier identity. This dossier describes the
        published market — it never predicts whether a bid will win.
      </p>
    </div>
  );
}
