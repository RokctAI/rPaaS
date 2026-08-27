# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""The outcome ledger read back as an honest per-strategy-version report.

Pure aggregation over ledger rows — no frappe, no site, reused verbatim by
the control-side admin endpoint (api/get_forex_retraining_report) and by
any offline harness fed a ledger export, so the desk report and the
harness can never disagree about what the ledger says. The same
arrangement as the zones retraining report.

Honesty rules, baked in rather than promised:

* **Grouped per strategy VERSION** (strategy_id + spec checksum from the
  immutable catalog), never pooled across versions — a parameter set is
  graded only on trades it actually made.
* **Every settled signal counts.** The win rate's denominator is all
  settled signals — losses, scratches AND expiries included. An expired
  signal was still a signal the strategy emitted; leaving it out would
  quietly inflate every rate.
* **No smoothing, no minimum-variance tricks, no dropping outliers.**
  Averages are plain arithmetic means; the max-losing-streak is the real
  one.
* **Below a documented minimum the verdict is `insufficient_data`.**
  Counts are still reported (nothing divides by zero), but no rate below
  MIN_SETTLED_FOR_REPORT settled signals is presented as if it meant
  something — early win rates over a handful of trades are noise.
"""

import datetime as dt


def _load_sibling(module_name, filename):
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:  # composed as a package
    from . import ledger as _ledger
except ImportError:  # standalone reuse (tests, offline harness)
    _ledger = _load_sibling("rforex_outcomes_ledger", "ledger.py")

#: a version earns real rates only once the ledger holds at least this many
#: SETTLED signals for it; below that the state is insufficient_data. Also
#: the recommended per-version volume before a retune is worth considering
#: (mirrors the zones ledger's minimum-judgements gate).
MIN_SETTLED_FOR_REPORT = 20

STATE_REPORTED = "reported"
STATE_INSUFFICIENT = "insufficient_data"


def _mean(values):
    return sum(values) / len(values) if values else None


def _round(value, digits=3):
    return None if value is None else round(value, digits)


def summarize_version(rows):
    """Observed performance of ONE strategy version from its ledger rows.

    rows: ledger rows (dicts shaped like ledger.FIELDS) already filtered to
    one (strategy_id, strategy_checksum). Pure; never divides by zero.

    Metric definitions (fixed here, not tunable):
      win_rate            wins / settled — scratches and expiries stay in
                          the denominator.
      average_pips        arithmetic mean of `pips` over settled rows that
                          carry a pips value.
      expectancy_pips     mean pips per settled signal with a missing pips
                          value counted as 0 — what one emitted-and-settled
                          signal was actually worth, on average.
      max_consecutive_losses
                          longest run of `loss` verdicts in entry order;
                          any other settled verdict breaks the run, open
                          signals are skipped (they have no verdict yet).
    """
    settled = [r for r in rows if r.get("outcome")]
    open_rows = [r for r in rows if not r.get("outcome")]

    counts = {
        "signals": len(rows),
        "open": len(open_rows),
        "settled": len(settled),
    }
    for name in _ledger.OUTCOMES:
        counts[name] = sum(1 for r in settled if r["outcome"] == name)

    n = len(settled)
    win_rate = (counts[_ledger.OUTCOME_WIN] / n) if n else None

    pips_known = [float(r["pips"]) for r in settled
                  if r.get("pips") is not None]
    average_pips = _mean(pips_known)
    expectancy = (sum(float(r["pips"] or 0) for r in settled) / n) if n else None

    streak = longest = 0
    for row in sorted(settled, key=_entry_order):
        if row["outcome"] == _ledger.OUTCOME_LOSS:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0

    period = _period(rows)

    if n < MIN_SETTLED_FOR_REPORT:
        state = STATE_INSUFFICIENT
        detail = ("insufficient data: {0} settled signal(s) on record, {1} "
                  "needed before any rate here means anything ({2} still "
                  "open)".format(n, MIN_SETTLED_FOR_REPORT, len(open_rows)))
    else:
        state = STATE_REPORTED
        detail = ("{0} settled signal(s): {1} win(s), {2} loss(es), {3} "
                  "scratch(es), {4} expired".format(
                      n,
                      counts[_ledger.OUTCOME_WIN],
                      counts[_ledger.OUTCOME_LOSS],
                      counts[_ledger.OUTCOME_SCRATCH],
                      counts[_ledger.OUTCOME_EXPIRED]))

    return {
        "counts": counts,
        "win_rate": _round(win_rate),
        "average_pips": _round(average_pips, 1),
        "expectancy_pips": _round(expectancy, 1),
        "max_consecutive_losses": longest,
        "period": period,
        "min_settled_for_report": MIN_SETTLED_FOR_REPORT,
        "state": state,
        "detail": detail,
    }


def _entry_order(row):
    parsed = _ledger._naive_utc(_ledger._parse_ts(row.get("entry_ts")))
    return (parsed is None, parsed or dt.datetime.min, row.get("name") or "")


def _period(rows):
    """{"from": earliest entry, "to": latest exit-or-entry} or Nones."""
    starts, ends = [], []
    for row in rows:
        entry = _ledger._naive_utc(_ledger._parse_ts(row.get("entry_ts")))
        if entry is not None:
            starts.append(entry)
            ends.append(entry)
        exit_ = _ledger._naive_utc(_ledger._parse_ts(row.get("exit_ts")))
        if exit_ is not None:
            ends.append(exit_)
    return {
        "from": min(starts).isoformat() if starts else None,
        "to": max(ends).isoformat() if ends else None,
    }


def group_by_version(rows):
    """{(strategy_id, strategy_checksum): [rows]} — the grouping every
    report uses. Rows missing either half of the identity are collected
    under ("_unidentified", "") rather than silently dropped."""
    groups = {}
    for row in rows:
        sid = (row or {}).get("strategy_id") or "_unidentified"
        checksum = (row or {}).get("strategy_checksum") or ""
        if not (row or {}).get("strategy_id") or not checksum:
            key = ("_unidentified", "")
        else:
            key = (sid, checksum)
        groups.setdefault(key, []).append(row)
    return groups


def get_strategy_report(strategy_id, rows=None):
    """Per-version performance for one strategy.

    rows defaults to the live ledger (ledger.list_signals); pass an
    explicit list to run over an export instead. Versions are keyed by
    their catalog spec_checksum — the identity a running bot verifies.
    """
    if rows is None:
        rows = _ledger.list_signals(strategy_id=strategy_id)
    else:
        rows = [r for r in rows if (r or {}).get("strategy_id") == strategy_id]

    versions = {}
    for (sid, checksum), group in group_by_version(rows).items():
        if sid != strategy_id:
            continue
        versions[checksum] = summarize_version(group)

    return {
        "strategy_id": strategy_id,
        "total_signals": len(rows),
        "versions": versions,
        "min_settled_for_report": MIN_SETTLED_FOR_REPORT,
    }


def build_report(rows):
    """The full admin payload from raw ledger rows. Pure.

    One block per strategy version plus a plain-language summary — the
    thing a human reads to decide whether a retune is worth considering.
    Nothing in here triggers anything.
    """
    groups = group_by_version(rows)
    strategies = {}
    unidentified = 0
    for (sid, checksum), group in sorted(groups.items()):
        if sid == "_unidentified":
            unidentified += len(group)
            continue
        strategies.setdefault(sid, {})[checksum] = summarize_version(group)

    lines = ["Forex outcome ledger: {0} signal(s) on record.".format(
        len(rows))]
    for sid in sorted(strategies):
        for checksum, summary in sorted(strategies[sid].items()):
            label = ("INSUFFICIENT DATA"
                     if summary["state"] == STATE_INSUFFICIENT
                     else "REPORTED")
            win = summary["win_rate"]
            exp = summary["expectancy_pips"]
            lines.append(
                "{0} @ {1}: {2} - {3}; win rate {4}, expectancy {5} pip(s), "
                "max losing streak {6}.".format(
                    sid, (checksum[:12] + "...") if len(checksum) > 15
                    else checksum,
                    label, summary["detail"],
                    "n/a" if win is None else "{0:.1%}".format(win),
                    "n/a" if exp is None else exp,
                    summary["max_consecutive_losses"]))
    if unidentified:
        lines.append("{0} row(s) lacked a strategy id or version checksum "
                     "and were left out of the per-version figures.".format(
                         unidentified))
    lines.append("Rates below {0} settled signals are withheld, not "
                 "estimated. Retuning is a human decision and always ships "
                 "as a NEW strategy version — see forex/BACKTEST.md.".format(
                     MIN_SETTLED_FOR_REPORT))

    return {
        "admin_only": True,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(
            microsecond=0).isoformat(),
        "total_signals": len(rows),
        "min_settled_for_report": MIN_SETTLED_FOR_REPORT,
        "strategies": strategies,
        "unidentified_rows": unidentified,
        "summary": "\n".join(lines),
    }
