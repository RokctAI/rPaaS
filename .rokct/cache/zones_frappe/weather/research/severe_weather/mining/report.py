"""SIGNATURES.md generator: evidence report from a mining run's results directory.

Reads composites.parquet, auc_by_lead.parquet, rankings.csv, run_meta.json and writes
SIGNATURES.md (plus small composite-curve PNGs under results/plots/ when matplotlib
is available). Purely a renderer - no data access, so the holdout guard is untouched.

Usage: python3 report.py [--results DIR] [--out PATH] [--top N] [--no-plots]
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from features import FEATURES

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

#: physical interpretation per feature family
FAMILY_INTERPRETATION = {
    "rain": "direct rainfall loading - sustained or intense antecedent precipitation",
    "wetness": "antecedent wetness / persistence of rainy conditions",
    "soil": "soil saturation state - controls how much of new rain becomes runoff",
    "pressure": "synoptic-scale cyclone approach / deepening (pressure falls precede wind and rain)",
    "wind": "strengthening low-level flow ahead of or during the event",
    "shear": "gustiness / directional-veer stand-ins for vertical shear (no 100 m wind extracted)",
    "moisture": "low-level moisture and instability proxies (ERA5 has no CAPE)",
    "boundary_layer": "boundary-layer depth / mixing regime",
    "snow": "snowpack and melt-driven runoff contribution",
    "interaction": "compound signal: rain falling on already-saturated soil (runoff efficiency)",
}

CURVE_POINTS = [-168, -72, -48, -24, -12, -6, 0]


def _fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    return f"{x:.{nd}f}"


def _auc_lead_table(auc: pd.DataFrame, klass: str, feats: list[str]) -> str:
    leads = sorted(auc["lead_h"].unique())
    head = "| feature | " + " | ".join(f"AUC @-{h}h" for h in leads) + " |"
    sep = "|---" * (len(leads) + 1) + "|"
    lines = [head, sep]
    sub = auc[auc["event_class"] == klass].set_index(["feature", "lead_h"])
    for ft in feats:
        cells = []
        for h in leads:
            try:
                r = sub.loc[(ft, h)]
                cells.append(f"{r['auc']:.3f}")
            except KeyError:
                cells.append("-")
        lines.append(f"| `{ft}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _curve_lines(comp: pd.DataFrame, klass: str, ft: str) -> str:
    sub = comp[(comp["event_class"] == klass) & (comp["feature"] == ft)]
    ev = sub[sub["role"] == "event"].set_index("rel_h")
    ct = sub[sub["role"] == "control"].set_index("rel_h")
    pts = [h for h in CURVE_POINTS if h in ev.index]
    head = "| rel hour | " + " | ".join(str(h) for h in pts) + " |"
    sep = "|---" * (len(pts) + 1) + "|"
    ev_row = "| event median | " + " | ".join(_fmt(ev.loc[h, "median"]) for h in pts) + " |"
    ci_row = ("| event IQR | " + " | ".join(
        f"{_fmt(ev.loc[h, 'q25'])}..{_fmt(ev.loc[h, 'q75'])}" for h in pts) + " |")
    ct_row = "| control median | " + " | ".join(_fmt(ct.loc[h, "median"]) for h in pts) + " |"
    return "\n".join([head, sep, ev_row, ci_row, ct_row])


def _plot(comp: pd.DataFrame, klass: str, ft: str, path: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    sub = comp[(comp["event_class"] == klass) & (comp["feature"] == ft)]
    fig, ax = plt.subplots(figsize=(6, 2.6), dpi=110)
    for role, color in (("event", "#c0392b"), ("control", "#2c3e50")):
        s = sub[sub["role"] == role].sort_values("rel_h")
        ax.plot(s["rel_h"], s["median"], color=color, lw=1.4, label=role)
        ax.fill_between(s["rel_h"], s["q25"], s["q75"], color=color, alpha=0.15, lw=0)
    ax.axvline(0, color="k", lw=0.6, ls="--")
    ax.set_xlabel("hours relative to onset")
    ax.set_title(f"{klass}: {ft}", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def generate(results_dir: str = RESULTS_DIR, out_path: str | None = None,
             top_n: int = 8, plots: bool = True, rank_lead: int = 24) -> str:
    out_path = out_path or os.path.join(os.path.dirname(results_dir), "SIGNATURES.md")
    comp = pd.read_parquet(os.path.join(results_dir, "composites.parquet"))
    auc = pd.read_parquet(os.path.join(results_dir, "auc_by_lead.parquet"))
    with open(os.path.join(results_dir, "run_meta.json")) as f:
        meta = json.load(f)

    plot_dir = os.path.join(results_dir, "plots")
    lines = ["# Precursor signatures - mining evidence report", ""]
    if meta.get("partial"):
        lines += [
            "> **PARTIAL DATA - NOT THE FINAL ANSWER.** Extraction was still running: "
            f"only {meta['dev_series_extracted']}/{meta['dev_series_in_manifest']} dev "
            "series were available to this run. Rankings will shift; regenerate after "
            "the extraction completes and finalize_series.py has run.", ""]
    lines += [
        f"Generated {meta['generated_utc']} UTC from `{os.path.relpath(results_dir, HERE)}`. "
        f"Dev cohort only (holdout 2018+ untouched, enforced in `data.py`). "
        f"{meta['n_features']} candidate features; leads {meta['leads_h']} h; "
        "AUC = P(event value > control value) at the given lead, computed on values at "
        "rel hour -lead (onset-aligned; controls aligned on their pseudo-onset).",
        "",
        "## Series used", "",
        "| class | events | controls |", "|---|---|---|"]
    for k, c in meta["counts_used"].items():
        lines.append(f"| {k} | {c['event']} | {c['control']} |")
    lines.append("")

    for klass in meta["classes"]:
        a = auc[(auc["event_class"] == klass)
                & (auc["n_event"] >= 20) & (auc["n_control"] >= 20)]
        lines += [f"## {klass}", ""]
        if a.empty:
            lines += ["Not enough extracted series yet (need >= 20 events and 20 "
                      "controls with valid values at each lead).", ""]
            continue
        at_lead = a[a["lead_h"] == rank_lead]
        if at_lead.empty:
            at_lead = a[a["lead_h"] == a["lead_h"].min()]
        top = at_lead.sort_values("abs_auc", ascending=False).head(top_n)
        lines += [f"### Top {len(top)} features (ranked by |AUC-0.5| at -{rank_lead} h)", "",
                  _auc_lead_table(auc, klass, top["feature"].tolist()), ""]
        for _, r in top.head(5).iterrows():
            ft = r["feature"]
            family, desc = FEATURES[ft]
            direction = "higher" if r["auc"] > 0.5 else "lower"
            lines += [
                f"#### `{ft}` - {desc}",
                "",
                f"AUC {r['auc']:.3f} at -{int(r['lead_h'])} h "
                f"(Cliff's delta {r['cliffs_delta']:+.2f}, robust d {_fmt(r['robust_d'])}; "
                f"n={r['n_event']}/{r['n_control']}). Events run **{direction}** than "
                f"controls (median {_fmt(r['median_event'])} vs {_fmt(r['median_control'])}).",
                "",
                _curve_lines(comp, klass, ft),
                "",
                f"*Physical reading ({family}):* {FAMILY_INTERPRETATION[family]}.", ""]
            if plots:
                os.makedirs(plot_dir, exist_ok=True)
                png = os.path.join(plot_dir, f"{klass}_{ft}.png")
                if _plot(comp, klass, ft, png):
                    lines += [f"![{klass} {ft}]({os.path.relpath(png, os.path.dirname(out_path))})", ""]

        # negative results, per the plan: features that do NOT separate
        best = (a.groupby("feature")["abs_auc"].max())
        flat = sorted(best[best < 0.55].index)
        if flat:
            lines += ["### Non-separating features (|AUC-0.5| < 0.05 at every lead)", "",
                      ", ".join(f"`{ft}`" for ft in flat),
                      "", "Recorded to prevent re-derivation churn.", ""]

    text = "\n".join(lines) + "\n"
    with open(out_path, "w", newline="\n") as f:
        f.write(text)
    print(f"wrote {out_path}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default=RESULTS_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()
    generate(args.results, args.out, args.top, plots=not args.no_plots)


if __name__ == "__main__":
    main()
