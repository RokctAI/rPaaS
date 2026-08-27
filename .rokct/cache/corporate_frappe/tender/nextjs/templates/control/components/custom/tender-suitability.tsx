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

import { useState, useTransition } from "react";
import Link from "next/link";
import { FiAlertTriangle, FiBarChart2, FiInfo } from "react-icons/fi";

import { getTenderSuitability } from "@/app/actions/opportunities/bids";
import type { TenderSuitability } from "@/app/services/control/bids";

// "Check my fit" - renders the two-stage suitability payload from
// control:get_tender_suitability: hard gates (no_bid with every firing
// reason, never a fake score), the renormalised 0-100 fit score with
// per-dimension reasons, the market_context block (typical winning-price
// band from the published award record, buyer publication behaviour,
// entrant share), the confidence flag with the advert-only triage note,
// and the manual checks. All scoring happens server-side against the
// caller's Tender Business Profile - this component only displays it.

const BAND_STYLES: Record<string, string> = {
  strong: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  review: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  marginal: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  poor: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  no_bid: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  unscored: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-500",
};

const BAND_LABELS: Record<string, string> = {
  strong: "Strong fit",
  review: "Worth reviewing",
  marginal: "Marginal fit",
  poor: "Poor fit",
  no_bid: "No-bid",
  unscored: "Not scorable yet",
};

const DIMENSION_LABELS: Record<string, string> = {
  sector_fit: "Sector fit",
  readiness: "Document readiness",
  process_feasibility: "Process feasibility",
  geography_fit: "Geography",
  buyer_burden: "Buyer burden",
  engagement_economics: "Engagement economics",
  pack_informed: "Pack-informed demands",
};

const BAND_LEVEL_LABELS: Record<string, string> = {
  buyer: "this buyer's published awards",
  category_province: "same category and province",
  category: "same category (all provinces)",
  province: "same province (all categories)",
};

const PUBLICATION_LABELS: Record<string, string> = {
  high: "publishes most award outcomes",
  medium: "publishes some award outcomes",
  low: "rarely publishes award outcomes",
  zero: "publishes award outcomes on its own website, not the central feed",
  unknown: "award-publication behaviour unknown",
};

export function formatRand(amount: number | null | undefined): string {
  if (amount == null || isNaN(amount)) return "—";
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `R${(amount / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `R${(amount / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `R${Math.round(amount / 1e3)}k`;
  return `R${Math.round(amount)}`;
}

function BandChip({ band, score }: { band: string; score: number | null }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${BAND_STYLES[band] ?? BAND_STYLES.unscored}`}
    >
      {BAND_LABELS[band] ?? band}
      {score != null && <span className="font-normal">· {score}/100</span>}
    </span>
  );
}

function DimensionRow({ name, dim }: { name: string; dim: any }) {
  const pctWidth = dim.known && dim.max ? Math.round((100 * (dim.points ?? 0)) / dim.max) : 0;
  const detail = dim.reasons?.[0]?.detail ?? "";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">
          {DIMENSION_LABELS[name] ?? name}
        </span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400 shrink-0">
          {dim.known ? `${dim.points}/${dim.max}` : "unknown"}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${dim.known ? "bg-purple-500" : "bg-zinc-300 dark:bg-zinc-700"}`}
          style={{ width: dim.known ? `${pctWidth}%` : "100%", opacity: dim.known ? 1 : 0.25 }}
        />
      </div>
      {detail && (
        <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-snug">{detail}</p>
      )}
    </div>
  );
}

function MarketContextPanel({ market }: { market: TenderSuitability["market_context"] }) {
  if (!market?.available) return null;
  const buyer = market.buyer_stats;
  const band = market.price_band;
  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
        <FiBarChart2 className="h-4 w-4 text-purple-500" />
        Market context
        <span className="text-xs font-normal text-zinc-400">
          from {market.dataset?.awards?.toLocaleString?.() ?? "32,589"} published awards
          (snapshot {market.dataset?.snapshot_date})
        </span>
      </div>

      {band ? (
        <div className="text-sm text-zinc-700 dark:text-zinc-300">
          <span className="font-medium">Typical winning value:</span>{" "}
          {formatRand(band.median_rand)}{" "}
          <span className="text-zinc-500 dark:text-zinc-400">
            (middle half {formatRand(band.iqr_rand?.[0])} – {formatRand(band.iqr_rand?.[1])},
            from {band.n} awards in {BAND_LEVEL_LABELS[band.level] ?? band.level})
          </span>
        </div>
      ) : (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No comparable price benchmark for this buyer, category and province — too few
          published awards to say anything honest.
        </p>
      )}

      {buyer && (
        <div className="text-sm text-zinc-700 dark:text-zinc-300 flex flex-col gap-1">
          <div>
            <span className="font-medium">
              {buyer.matched && buyer.buyer ? buyer.buyer : "This buyer"}:
            </span>{" "}
            {PUBLICATION_LABELS[buyer.publication_behavior] ?? PUBLICATION_LABELS.unknown}
            {buyer.publication_rate_pct != null && buyer.publication_rate_pct > 0 && (
              <span className="text-zinc-500 dark:text-zinc-400">
                {" "}({buyer.publication_rate_pct}% of its tenders show a published award)
              </span>
            )}
          </div>
          {buyer.entrant_share_pct != null && (
            <div className="text-zinc-500 dark:text-zinc-400">
              Small entrants win {buyer.entrant_share_pct}% of published awards{" "}
              {buyer.matched ? "at this buyer" : "across the market"}
              {buyer.incumbency_share_pct != null &&
                ` · ${buyer.incumbency_share_pct}% go to repeat suppliers here`}
            </div>
          )}
        </div>
      )}

      <p className="text-[11px] leading-snug text-zinc-400 dark:text-zinc-500">
        Based on the public eTenders award record, which only shows published successes —
        it prices the market and never predicts whether a bid will win.
      </p>
    </div>
  );
}

export function TenderSuitabilityCheck({
  slug,
  opportunityType = "tenders",
  loggedIn,
}: {
  slug: string;
  opportunityType?: "tenders" | "grants" | "equity";
  loggedIn: boolean;
}) {
  const [result, setResult] = useState<TenderSuitability | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const runCheck = () => {
    setError(null);
    startTransition(async () => {
      const res: any = await getTenderSuitability(slug, opportunityType);
      if (res?.error) {
        setError(res.error);
        setResult(null);
      } else {
        setResult(res as TenderSuitability);
      }
    });
  };

  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 p-5 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wide">
          Check my fit
        </h2>
        {result && <BandChip band={result.band} score={result.score} />}
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
        Rates this opportunity against your business profile: hard eligibility gates first,
        then a fit score with the market context from published award outcomes.
      </p>

      {!loggedIn ? (
        <Link
          href="/login"
          className="inline-flex rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        >
          Sign in to check your fit
        </Link>
      ) : !result ? (
        <div className="flex flex-col gap-3">
          <button
            onClick={runCheck}
            disabled={pending}
            className="self-start rounded-lg bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 transition-colors"
          >
            {pending ? "Checking your fit…" : "Check my fit"}
          </button>
          {error && (
            <p className="text-sm text-amber-700 dark:text-amber-400">{error}</p>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Confidence + triage */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-medium ${
                result.confidence === "pack_verified"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
              }`}
            >
              {result.confidence === "pack_verified" ? "Pack-verified" : "Advert only"}
            </span>
            {result.days_to_close != null && (
              <span className="text-zinc-500 dark:text-zinc-400">
                {result.days_to_close} day{result.days_to_close === 1 ? "" : "s"} to close
              </span>
            )}
          </div>
          {result.confidence === "advert_only" && result.triage && (
            <p className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400 leading-snug">
              <FiInfo className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              This is an advert-level score — its job is deciding whether the full tender
              pack is worth fetching. Once the pack is in, the score is re-run at full
              confidence.
            </p>
          )}

          {/* No-bid gates: every firing reason, no fake score */}
          {result.band === "no_bid" && (
            <div className="rounded-lg border border-red-200 dark:border-red-900/40 bg-red-50 dark:bg-red-900/10 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-red-700 dark:text-red-300 mb-2">
                <FiAlertTriangle className="h-4 w-4" />
                Why this is a no-bid
              </div>
              <ul className="flex flex-col gap-1.5">
                {result.hard_failures.map((f, i) => (
                  <li key={i} className="text-sm text-red-700 dark:text-red-300 leading-snug">
                    {f.detail}
                  </li>
                ))}
              </ul>
              {!result.profile_completeness?.complete && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                  Missing on your profile: {result.profile_completeness.missing.join(", ")} —
                  completing your business profile fixes this for every tender at once.
                </p>
              )}
            </div>
          )}

          {/* Fit dimensions */}
          {result.band !== "no_bid" && (
            <div className="flex flex-col gap-3">
              {Object.entries(result.dimensions ?? {}).map(([name, dim]) => (
                <DimensionRow key={name} name={name} dim={dim} />
              ))}
            </div>
          )}

          {/* Market context */}
          <MarketContextPanel market={result.market_context} />

          {/* Manual checks */}
          {result.manual_checks?.length > 0 && (
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4">
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">
                Still to verify by hand
              </h3>
              <ul className="flex flex-col gap-1.5">
                {result.manual_checks.map((m, i) => (
                  <li key={i} className="text-xs text-zinc-600 dark:text-zinc-400 leading-snug">
                    <span className="font-medium text-zinc-700 dark:text-zinc-300">
                      {m.title ?? m.code}
                    </span>
                    {m.checklist_text ? ` — ${m.checklist_text}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {result.warnings?.length > 0 && (
            <ul className="flex flex-col gap-1">
              {result.warnings.map((w, i) => (
                <li key={i} className="text-xs text-zinc-500 dark:text-zinc-400 leading-snug">
                  {w}
                </li>
              ))}
            </ul>
          )}

          <button
            onClick={runCheck}
            disabled={pending}
            className="self-start text-xs text-purple-600 dark:text-purple-400 hover:underline disabled:opacity-60"
          >
            {pending ? "Re-checking…" : "Re-check"}
          </button>
        </div>
      )}
    </div>
  );
}
