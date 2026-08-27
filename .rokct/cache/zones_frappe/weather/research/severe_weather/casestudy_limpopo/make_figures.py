"""Precursor-timeline figures for the Limpopo blind case study (reporting only).

One small PNG per documented event: the feature time series the frozen flood
rules watch, with their frozen ON thresholds, detector warning shading, and the
documented onset. Shows for each event whether precursors crossed or merely
approached the thresholds - no retuning is done or implied.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import matplotlib.dates as mdates        # noqa: E402
import pandas as pd                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")

# reference dataviz palette (light mode)
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#898781", "#e1e0d9"
S1, S2 = "#2a78d6", "#eb6834"            # categorical slots 1-2
THRESH = "#d03b3b"                       # critical (threshold line)
SHADE = "#ec835a"                        # serious (warning episode shading)

#: (event id, point, era, window, onset(s))
PANELS = [
    ("1977", "chokwe", "e1977", ("1977-01-15", "1977-03-05"),
     [("rain onset 1 Feb", "1977-02-01"), ("Chokwe flooded 12 Feb", "1977-02-12")]),
    ("2000", "chokwe", "modern", ("2000-01-20", "2000-03-10"),
     [("rain onset 8 Feb", "2000-02-08"), ("Limpopo floods Chokwe 12 Feb", "2000-02-12"),
      ("post-Eline crest 25 Feb", "2000-02-25")]),
    ("2013", "chokwe", "modern", ("2012-12-28", "2013-02-15"),
     [("rain onset 14 Jan", "2013-01-14"), ("Chokwe evacuated 22 Jan", "2013-01-22")]),
    ("2026", "thohoyandou", "modern", ("2025-12-15", "2026-02-05"),
     [("SAWS L9, Vhembe floods 12 Jan", "2026-01-12")]),
    ("2026_lower", "chokwe", "modern", ("2025-12-20", "2026-02-10"),
     [("Xai-Xai evacuation order 20 Jan", "2026-01-20")]),
]

#: frozen ON thresholds (read from detector_config_tuned.json; duplicated here
#: for plotting only - the detector run reads the config file itself)
FLOOD_ON = {"precip_sum_24h": 78.481, "precip_sum_48h": 45.4787,
            "rain_on_sat_24h": 22.1904, "rain_on_sat_72h": 39.5838}
FF_ON = {"nbr_max_sum_12h": 42.115, "nbr_rain_on_sat_6h": 13.4671,
         "tcwv_anom_7d": 12.9108}


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.6)


def panel(ax, f, cols, thresholds, title):
    for col, color in zip(cols, (S1, S2)):
        ax.plot(f.index, f[col], color=color, linewidth=1.1, label=col)
    for col in cols:
        if col in thresholds:
            ax.axhline(thresholds[col], color=THRESH, linewidth=0.9,
                       linestyle="--", alpha=0.85)
            ax.annotate(f"{col} ON = {thresholds[col]:.1f}",
                        xy=(0.005, thresholds[col]),
                        xycoords=("axes fraction", "data"),
                        fontsize=6, color=THRESH, va="bottom")
    ax.set_title(title, fontsize=8, color=INK, loc="left")
    ax.legend(fontsize=6, loc="upper right", frameon=False, labelcolor=INK)
    style(ax)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    alarms = pd.read_csv(os.path.join(HERE, "alarms.csv"),
                         parse_dates=["first_fired_at", "last_active_at"])
    for ev, point, era, (w0, w1), onsets in PANELS:
        f = pd.read_parquet(os.path.join(HERE, "features",
                                         f"{point}_{era}.parquet"))
        f = f.loc[w0:w1]
        fig, axes = plt.subplots(3, 1, figsize=(7.4, 6.2), sharex=True,
                                 facecolor=SURFACE)
        panel(axes[0], f, ["precip_sum_24h", "precip_sum_48h"], FLOOD_ON,
              f"{point} - rain accumulation (mm)")
        panel(axes[1], f, ["rain_on_sat_24h", "rain_on_sat_72h"], FLOOD_ON,
              "rain-on-saturated-soil (mm x soil pct)")
        panel(axes[2], f, ["nbr_max_sum_12h", "tcwv_anom_7d"], FF_ON,
              "neighborhood 12 h rain max (mm) / TCWV anomaly (kg m-2)")
        # warning episodes (flood solid, flash_flood hatched) + onset markers
        al = alarms[(alarms["point"] == point)
                    & (alarms["first_fired_at"] <= pd.Timestamp(w1))
                    & (alarms["last_active_at"] >= pd.Timestamp(w0))
                    & (alarms["event_class"].isin(["flood", "flash_flood"]))]
        for ax in axes:
            for a in al.itertuples():
                ax.axvspan(a.first_fired_at, a.last_active_at, color=SHADE,
                           alpha=0.28 if a.event_class == "flood" else 0.14,
                           lw=0)
            for label, d in onsets:
                ax.axvline(pd.Timestamp(d), color=INK, linewidth=0.9,
                           linestyle=":", alpha=0.8)
        for label, d in onsets:
            axes[0].annotate(label, xy=(pd.Timestamp(d), 0.99),
                             xycoords=("data", "axes fraction"), fontsize=6,
                             color=INK, rotation=90, va="top", ha="right")
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.suptitle(f"Event {ev}: frozen-rule precursors at {point} "
                     "(shading = detector warning episodes)", fontsize=9,
                     color=INK, x=0.02, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        out = os.path.join(FIG_DIR, f"event_{ev}_{point}.png")
        fig.savefig(out, dpi=70, facecolor=SURFACE)
        plt.close(fig)
        print(out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
