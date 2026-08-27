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

// Frappe whitelisted responses may arrive as the bare value or wrapped in { message }.
const unwrap = (res: any) => (res && typeof res === "object" && "message" in res ? res.message : res);

export interface ChecklistItem {
  name: string;
  task_text: string;
  weight: number;
  status: "Open" | "Done";
}

// ── Bid-time pricing band, attached per bid by control:get_my_bids as an
// ADDITIVE enrichment: the typical winning-price band for the bid's
// buyer/category/province, compacted server-side from the market-context
// tables (PR #55 - median/IQR of published eTenders award amounts,
// aggregate public data only). Absent / null whenever no comparable cell
// reached the N>=30 discipline - clients render nothing then, never a
// placeholder number. Labels (median_label / iqr_label / headline) are
// pre-formatted server-side with the same formatRand convention as
// tender-suitability.tsx, so every surface prints the same figure.

export interface BidPricingBand {
  level: "buyer" | "category_province" | "category" | "province";
  basis: string;
  scope: string;
  median_rand: number;
  iqr_rand: [number, number] | null;
  n: number;
  median_label: string;
  iqr_label: string | null;
  headline: string;
  semantics: string;
  caveat: string;
  caveats: string[];
  dataset: { source: string; snapshot_date: string; awards: number };
}

export interface TenderBid {
  name: string;
  tender_slug: string;
  tender_title?: string;
  institution?: string;
  closing_date?: string;
  status: string;
  enrichment_level?: string;
  submitted_on?: string;
  outcome_value?: number;
  checklist?: ChecklistItem[];
  tasks_total?: number;
  tasks_done?: number;
  pricing_band?: BidPricingBand | null;
}

export interface PackFormStatus {
  form_code: string;
  form_name: string;
  mandatory: boolean;
  has_template: boolean;
  auto_total: number;
  auto_filled: number;
  user_input: string[];
  missing_auto: string[];
}

export interface PackManifest {
  bid: string;
  regime: string;
  regime_name?: string;
  generated_on?: string;
  form_count: number;
  forms: PackFormStatus[];
  fill: {
    auto_total: number;
    auto_filled: number;
    coverage_pct: number;
    user_input_total: number;
    missing_auto: string[];
  };
  open_fatal_gates: string[];
  signed: boolean;
  signature_provenance?: string;
  warnings: string[];
  has_profile?: boolean;
  has_signature_image?: boolean;
}

export interface TenderDetail {
  tender: Record<string, any>;
  tasks: { task_text: string; weight: number }[];
  enrichment_level: "ADVANCED" | "GENERIC";
  advanced_available: boolean;
  entitled: boolean;
  entitlement_reason: string;
  bid: { name: string; status: string } | null;
}

// ── Suitability ("Check my fit") payload, from control:get_tender_suitability.
// Two-stage worth-bidding triage: hard gates (band no_bid, score null, all
// firing reasons) then a 0-100 fit score renormalised over KNOWN factors,
// plus the market_context block derived from the published eTenders award
// record (typical winning-price band, buyer publication behaviour, entrant
// share). See corporate tender/Suitability-Scoring-Model.md.

export interface SuitabilityReason {
  code: string;
  status?: string;
  detail?: string;
  [key: string]: any;
}

export interface SuitabilityDimension {
  points: number | null;
  max: number;
  known: boolean;
  reasons: SuitabilityReason[];
}

export interface SuitabilityManualCheck {
  code: string;
  severity?: string;
  title?: string;
  checklist_text?: string;
  count?: number;
  codes?: string[];
}

export interface MarketPriceBand {
  level: "buyer" | "category_province" | "category" | "province";
  basis: string;
  median_rand: number;
  iqr_rand: [number, number];
  n: number;
  semantics: string;
}

export interface MarketBuyerStats {
  matched: boolean;
  match_type: "exact" | "alias" | "default";
  buyer: string | null;
  award_count: number | null;
  benchmark_count: number | null;
  entrant_share_pct: number | null;
  incumbency_share_pct: number | null;
  zero_amount_share_pct: number | null;
  publication_rate_pct: number | null;
  publication_behavior: "high" | "medium" | "low" | "zero" | "unknown";
  entrant_note?: string;
}

export interface MarketContext {
  available: boolean;
  reason?: string;
  dataset?: {
    source: string;
    snapshot_date: string;
    awards: number;
    benchmark_rows: number;
  };
  buyer_stats?: MarketBuyerStats;
  coarse_category?: string | null;
  price_band?: MarketPriceBand | null;
  caveats?: string[];
}

export interface TenderSuitability {
  slug: string;
  title?: string;
  institution?: string;
  closing_date?: string;
  score: number | null;
  band: "strong" | "review" | "marginal" | "poor" | "no_bid" | "unscored";
  eligible: boolean;
  opportunity_type: string;
  semantics: string;
  source_record_class?: string;
  confidence: "pack_verified" | "advert_only";
  days_to_close: number | null;
  known_weight: number;
  dimensions: Record<string, SuitabilityDimension>;
  hard_failures: SuitabilityReason[];
  gate_notes: SuitabilityReason[];
  profile_completeness: { complete: boolean; missing: string[]; note: string };
  manual_checks: SuitabilityManualCheck[];
  data_flags: SuitabilityReason[];
  triage: string | null;
  warnings: string[];
  market_context: MarketContext;
  enrichment_used: boolean;
  entitled: boolean;
  entitlement_reason: string;
}

// ── Renewal radar payload, from control:get_renewal_radar. A deterministic
// lead calendar recomputed from the renewal ledger (observed adverts, stated
// contract durations, median observed cycles, counter-based trust) - no
// model, no probabilities. See corporate tender/Award-Outcomes-Research.md
// section 8.

export interface RenewalTrust {
  confirmed: number;
  missed: number;
  resolved: number;
  hit_rate_pct: number | null;
}

export interface RenewalWatchEntry {
  name: string;
  buyer: string;
  buyer_normalized: string;
  category: string | null;
  anchor_ocid: string;
  anchor_date: string | null;
  source: "stated_duration" | "observed_cycle";
  stated_duration_months: number | null;
  predicted_date: string;
  predicted_window_start: string;
  predicted_window_end: string;
  status: "open";
  trust: RenewalTrust | null;
}

export interface RenewalRadar {
  watches: RenewalWatchEntry[];
  trust: Record<string, RenewalTrust>;
  summary: {
    open_total: number;
    upcoming: number;
    months_ahead: number;
    confirmed_total: number;
    missed_total: number;
  };
  semantics: string;
  caveats: string[];
  generated_on: string;
}

// ── Unified compliance calendar payload, from control:get_compliance_calendar.
// ASSEMBLY of the four existing date streams (bid closings, briefings,
// compliance-artifact expiries, renewal expected-advertisement windows) into
// one dated feed - deterministic, no new logic, per-user items scoped to the
// caller. The honesty axis is item_class: "commitment" rows are real dates on
// real obligations; "watch" rows (ONLY the renewal stream) are lead-calendar
// windows and must NEVER render as deadlines - the Award-Outcomes validation
// confirmed only 2 of 12 sampled due predictions.

export type CalendarStream =
  | "bid_closing"
  | "briefing"
  | "artifact_expiry"
  | "renewal_window";

export type CalendarItemClass = "commitment" | "watch";

export interface ComplianceCalendarEntry {
  date: string;
  days_away: number;
  stream: CalendarStream;
  item_class: CalendarItemClass;
  title: string;
  detail: string;
  ref: {
    doctype: string;
    name: string;
    tender_slug?: string;
    institution?: string | null;
    compulsory?: boolean;
    artifact_type?: string;
    status?: string | null;
    source?: string | null;
    predicted_window_start?: string | null;
    predicted_window_end?: string | null;
    trust?: RenewalTrust | null;
  };
}

export interface ComplianceCalendar {
  entries: ComplianceCalendarEntry[];
  summary: {
    total: number;
    shown: number;
    days_ahead: number;
    horizon: string;
    streams: Record<CalendarStream, number>;
    commitments: number;
    watches: number;
  };
  semantics: string;
  caveats: string[];
  generated_on: string;
}

// ── Low-competition finder payload, from control:get_low_competition_tenders.
// Deterministic FIELD-NARROWNESS scoring per catalog card from public
// requirements only (required CIDB grade, EME/QSE set-asides, B-BBEE
// prequalification, compulsory briefings, short windows, local content),
// crossed with the caller's own business profile. Describes how narrow the
// field of qualifying firms is - NEVER a win probability.

export type NarrownessTier = "wide" | "moderate" | "narrow" | "very_narrow";

export interface NarrownessSignal {
  code: string;
  points: number;
  detail: string;
  quoted?: string;
  [key: string]: any;
}

export interface FieldNarrowness {
  score: number;
  tier: NarrownessTier;
  signals: NarrownessSignal[];
  days_to_close: number | null;
  semantics: string;
}

export interface NarrowingRequirementCheck {
  code: string;
  met: boolean | null;
  detail: string;
}

export interface LowCompetitionOpportunity {
  slug: string | null;
  title?: string;
  institution?: string;
  province?: string;
  closing_date?: string;
  days_to_close: number | null;
  closed: boolean;
  narrowness: FieldNarrowness;
  requirements: {
    checks: NarrowingRequirementCheck[];
    caveats: string[];
    meets_narrowing_requirements: boolean;
  };
  opportunity: boolean;
  enrichment_used?: boolean;
  semantics: string;
}

export interface LowCompetitionRadar {
  opportunities: LowCompetitionOpportunity[];
  summary: {
    scanned: number;
    matching: number;
    returned: number;
    min_tier: NarrownessTier;
  };
  entitled: boolean;
  entitlement_reason: string;
  semantics: string;
  caveats: string[];
  generated_on: string;
}

// ── Buyer dossier payload, from control:get_buyer_dossier. Per-buyer
// behavioural stats computed deterministically at build time from the
// committed public eTenders awards dataset (tools/build_buyer_dossiers.py):
// aggregate public data only, medians/IQR never means, every stat N-gated.
// The caveats ride every payload - winner-side data, publication bias,
// proxy semantics - and must be surfaced, not swallowed.

export interface BuyerDossierEntry {
  buyer: string;
  award_count: number;
  benchmark_count: number;
  median_rand: number | null;
  iqr_rand: [number, number] | null;
  zero_amount_share_pct: number | null;
  identified_award_count: number;
  placeholder_award_count: number;
  placeholder_share_pct: number | null;
  distinct_supplier_count: number | null;
  top_supplier: string | null;
  top_supplier_share_pct: number | null;
  single_win_supplier_share_pct: number | null;
}

export interface BuyerDossier {
  available: boolean;
  reason?: string;
  matched?: boolean;
  match_type?: "exact" | "alias" | "none";
  buyer_input?: string;
  dossier?: BuyerDossierEntry | null;
  dataset?: {
    source: string;
    snapshot_date: string;
    awards: number;
    buyers: number;
    min_amount_n: number;
    min_concentration_n: number;
  };
  semantics?: string;
  caveats?: string[];
  generated_on?: string;
  // Renewal Watch hook (additive): counter-based trust over this buyer's
  // resolved re-advertisement predictions plus its median lateness
  // correction, where the renewal ledger holds any. Null / absent when
  // nothing resolved yet.
  renewal?: {
    trust: RenewalTrust;
    lateness_days: number | null;
    semantics: string;
  } | null;
}

// ── Award-outcome ledger payload, from control:get_award_ledger (plan #12).
// Two halves: (i) counters over the caller's OWN bids (win rate over
// DECIDED bids only, per-buyer counters, quoted-vs-awarded deltas placed
// against the pricing bands the bid was shown) - per-subscriber PRIVATE
// data, served only to its owner; (ii) published-award matches - the
// claimed tenders' ocids joined against re-fetched OCDS releases to record
// who actually won (non-empty awards[] is the only signal; "no award
// published" is NEVER "lost"; the feed carries no award dates - the
// release date is the proxy). Market-context-style calibration and the
// user's own record - NEVER a win probability; the caveats ride every
// payload and must be surfaced, not swallowed.

export interface AwardLedgerBandPosition {
  ratio_to_median_pct: number;
  position: "below_iqr" | "within_iqr" | "above_iqr" | null;
  band_level: string;
  band_median_rand: number;
}

export interface AwardLedgerDeltaRow {
  bid: string;
  tender_slug: string;
  tender_title?: string | null;
  institution?: string | null;
  quoted_rand: number | null;
  awarded_rand: number | null;
  delta_rand: number | null;
  delta_pct: number | null;
  quoted_band_position: AwardLedgerBandPosition | null;
  awarded_band_position: AwardLedgerBandPosition | null;
  band_headline: string | null;
}

export interface AwardLedgerBuyerRow {
  buyer: string;
  tracked: number;
  decided: number;
  awarded: number;
  lost: number;
  rate_pct: number | null;
}

export interface AwardLedgerOwnOutcomes {
  tracked: number;
  by_status: Record<string, number>;
  decided: number;
  awaiting_outcome: number;
  win_rate: {
    awarded: number;
    decided: number;
    rate_pct: number;
    semantics: string;
  } | null;
  per_buyer: AwardLedgerBuyerRow[];
  quoted_vs_awarded: AwardLedgerDeltaRow[];
  privacy: string;
}

export interface AwardLedgerAward {
  winner: string | null;
  winner_placeholder: boolean;
  supplier_count: number;
  value_rand: number | null;
  currency: string | null;
  amount_flag: "zero" | "lt_R100" | "gt_R10bn" | "missing" | null;
  value_usable: boolean;
  status: string | null;
  award_date: null; // structurally absent from this feed
  date_proxy: string | null; // release date - the only (weak) time proxy
}

export interface AwardLedgerMatch {
  bid: string;
  tender_slug: string;
  tender_title?: string | null;
  institution?: string | null;
  bid_status: string;
  ocid: string | null;
  release_cached: boolean;
  release_date: string | null;
  published_award: boolean;
  awards: AwardLedgerAward[];
  note: string;
}

export interface AwardLedger {
  own_outcomes: AwardLedgerOwnOutcomes;
  published_matches: {
    matches: AwardLedgerMatch[];
    summary: {
      claimed: number;
      with_ocid: number;
      release_cached: number;
      published_award: number;
      no_award_published: number;
    };
  };
  semantics: string;
  caveats: string[];
  generated_on: string;
}

// Gateway contract: control sites only serve cmds carrying the `control:`
// prefix (see app/services/base/platform-gateway.ts and control hooks.py).
// The dotted `control.control.api.tenders.*` forms were never registered on
// the gateway and failed silently - these `control:` cmds are the canonical,
// registered names.
export class TenderBidService {
  static async getTenderDetail(slug: string): Promise<TenderDetail> {
    return unwrap(
      await ControlBaseService.call("control:get_tender_detail", { slug }),
    );
  }

  // Automated suitability check ("Check my fit") - rates one opportunity
  // card (tender / grant / equity) against the caller's Tender Business
  // Profile. Enrichment feeds the score server-side for entitled callers
  // only (never leaks); everyone else gets an advert-level score.
  static async getTenderSuitability(
    slug: string,
    opportunityType: "tenders" | "grants" | "equity" = "tenders",
  ): Promise<TenderSuitability> {
    return unwrap(
      await ControlBaseService.call("control:get_tender_suitability", {
        slug,
        opportunity_type: opportunityType,
      }),
    );
  }

  // Renewal radar: open renewal watches (predicted re-advertisements)
  // within the horizon, soonest first, with per-buyer trust counters. The
  // control plane only reads ledger state here - all prediction math ran
  // deterministically at sync time.
  static async getRenewalRadar(monthsAhead = 12): Promise<RenewalRadar> {
    return unwrap(
      await ControlBaseService.call("control:get_renewal_radar", {
        months_ahead: monthsAhead,
      }),
    );
  }

  // Unified compliance calendar: the four existing date streams merged into
  // one dated feed, soonest first. Per-user rows are the caller's own; the
  // renewal stream's rows carry item_class "watch" and must render as
  // prepare-now windows, never as deadlines.
  static async getComplianceCalendar(
    daysAhead = 90,
    limit = 200,
  ): Promise<ComplianceCalendar> {
    return unwrap(
      await ControlBaseService.call("control:get_compliance_calendar", {
        days_ahead: daysAhead,
        limit,
      }),
    );
  }

  // Low-competition finder: catalog cards whose field of qualifying firms
  // is narrow (from public requirements only) AND whose narrowing
  // requirements the caller's profile actually clears, narrowest field
  // first. Deterministic; describes the field, never a win probability.
  static async getLowCompetitionTenders(
    minTier: NarrownessTier = "narrow",
    limit = 20,
  ): Promise<LowCompetitionRadar> {
    return unwrap(
      await ControlBaseService.call("control:get_low_competition_tenders", {
        min_tier: minTier,
        limit,
      }),
    );
  }

  // Buyer dossier: per-buyer behavioural stats from the published award
  // record (award volume, typical award value, supplier concentration,
  // newcomer-openness proxy). Pure fixture lookup on the control plane -
  // nothing is computed per request, nothing is per-subscriber.
  static async getBuyerDossier(buyer: string): Promise<BuyerDossier> {
    return unwrap(
      await ControlBaseService.call("control:get_buyer_dossier", { buyer }),
    );
  }

  // Award-outcome ledger: the caller's own outcome counters plus the
  // published-award matches for their claimed ocids. Login-required and
  // scoped server-side to the session user's own bids (get_my_bids
  // doctrine); the payload's caveats must be rendered alongside any number.
  static async getAwardLedger(): Promise<AwardLedger> {
    return unwrap(
      await ControlBaseService.call("control:get_award_ledger", {}),
    );
  }

  static async claimTender(slug: string): Promise<TenderBid> {
    return unwrap(
      await ControlBaseService.call("control:claim_tender", { slug }),
    );
  }

  static async getMyBids(): Promise<TenderBid[]> {
    return unwrap(await ControlBaseService.call("control:get_my_bids", {}));
  }

  static async updateBidStatus(
    bid: string,
    status: string,
    extras: { submitted_on?: string; outcome_value?: number; outcome_notes?: string } = {},
  ): Promise<TenderBid> {
    return unwrap(
      await ControlBaseService.call("control:update_bid_status", {
        bid,
        status,
        ...extras,
      }),
    );
  }

  static async updateChecklistItem(bid: string, item: string, done: boolean) {
    return unwrap(
      await ControlBaseService.call("control:update_checklist_item", {
        bid,
        item,
        done: done ? 1 : 0,
      }),
    );
  }

  // Deterministic document-pack generator: the bid's form regime selects the
  // returnable forms, each pre-filled from the Tender Business Profile and
  // the bid's cached tender data. sign=true is the deliberate second step of
  // the review-then-sign flow - it stamps the profile's background-stripped
  // signature/initials images into the placement slots.
  static async generateBidPack(
    bid: string,
    sign = false,
  ): Promise<{ manifest: PackManifest; html: string }> {
    return unwrap(
      await ControlBaseService.call("control:generate_bid_pack", {
        bid,
        sign: sign ? 1 : 0,
      }),
    );
  }

  static async getPackStatus(bid: string): Promise<PackManifest> {
    return unwrap(await ControlBaseService.call("control:get_pack_status", { bid }));
  }

  // Soft erp integration: creates a draft Quotation pre-linked to the bid so
  // pricing happens in ERP. Fails with a clear message on sites without the
  // erp module - nothing else in the tender surface depends on it.
  static async createBidQuotation(
    bid: string,
  ): Promise<{ quotation: string; created: boolean }> {
    return unwrap(
      await ControlBaseService.call("control:create_bid_quotation", { bid }),
    );
  }

  // Per-buyer returnable reuse: previews (apply=false, default) or copies
  // (apply=true) the caller's most recent prior same-buyer bid's captured
  // custom returnables onto this bid. Strictly opt-in - nothing is ever
  // copied unless the user explicitly applies; seeded rows are a starting
  // point to verify against THIS pack.
  static async seedBidReturnables(
    bid: string,
    apply = false,
  ): Promise<{
    institution: string;
    source_bid: string | null;
    source_tender_title?: string;
    rows: Record<string, any>[];
    applied: number;
    note?: string;
  }> {
    return unwrap(
      await ControlBaseService.call("control:seed_bid_returnables", {
        bid,
        apply: apply ? 1 : 0,
      }),
    );
  }

  // Tiered, gated buyer-ward email (F-13). NOTHING sends unless confirmEmail
  // retypes the bid's stored buyer contact address. mode "pack" (attaches
  // the regenerated pack) additionally requires submission_channel "Email
  // allowed" AND a clean submission gate; mode "correspondence" sends a
  // plain written message (clarification questions etc.) and never attaches
  // the pack.
  static async dispatchBidPack(
    bid: string,
    mode: "pack" | "correspondence",
    confirmEmail: string,
    subject?: string,
    message?: string,
  ): Promise<{
    sent: boolean;
    mode: string;
    dispatched_to?: string;
    dispatched_on?: string;
    subject?: string;
    pack_attached?: boolean;
    reason?: string;
  }> {
    return unwrap(
      await ControlBaseService.call("control:dispatch_bid_pack", {
        bid,
        mode,
        confirm_email: confirmEmail,
        subject,
        message,
      }),
    );
  }
}
