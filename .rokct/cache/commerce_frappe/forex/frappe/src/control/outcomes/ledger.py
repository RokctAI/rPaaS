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

"""The forex outcome ledger: every emitted signal, logged against what
actually happened.

Ported discipline (the severe-weather outcome ledger in RokctAI/zones):
**evidence first, judgement later, nothing consumed automatically.** A row
is written the moment a strategy emits a signal — before anyone knows how
it ends — and settled exactly once when the position closes or the signal
dies. Nothing in this module retunes anything; the ledger exists so a
human reading the retraining report can decide whether a re-tune is even
worth considering.

Two rules are load-bearing and enforced here rather than by convention:

1. **A signal names the exact strategy version it came from.** Every row
   carries the strategy identifier AND the version's `spec_checksum` from
   the immutable catalog (`Forex Strategy Version`). Win rates are only
   meaningful per frozen parameter set — pooling outcomes across versions
   would grade a spec on trades it never made.
2. **A verdict is written once.** Settling an already-settled signal is
   refused, not overwritten. An "improved" ledger is a worthless one: the
   whole value of the table is that nobody, human or code, can massage it
   after the fact. Corrections happen the way they do in accounting — a
   new row and a note, never an edit (`meta` on the outcome is the note).

Storage follows the house pattern the rest of this SDK uses: a Frappe
DocType (`Forex Signal Outcome`, control plane, System Manager only) when
running composed with frappe and an active site, and an in-memory store
otherwise so the rules stay unit-testable with no site and no database —
the same guarded-import arrangement as the zones ledger consumers.

Validation mirrors `rforex.strategy_spec.validate_spec`: every problem is
returned as a human-readable string and the writer refuses the row unless
the list is empty. Fail closed — a half-described signal is not evidence.
"""

import datetime as dt
import json

try:  # composed into the control product
    import frappe
except ImportError:  # standalone / unit tests: in-memory store
    frappe = None

DOCTYPE = "Forex Signal Outcome"

# --- Vocabulary -------------------------------------------------------------

DIRECTION_LONG = "long"
DIRECTION_SHORT = "short"
DIRECTIONS = (DIRECTION_LONG, DIRECTION_SHORT)

OUTCOME_WIN = "win"          # target reached
OUTCOME_LOSS = "loss"        # stop reached
OUTCOME_SCRATCH = "scratch"  # closed flat-ish by rule or by hand
OUTCOME_EXPIRED = "expired"  # pending order never triggered / signal timed out
OUTCOMES = (OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_SCRATCH, OUTCOME_EXPIRED)

#: the row fields shared by both storage backends. One shape, so the report
#: code cannot care where a row came from.
FIELDS = (
    "name",
    "strategy_id",
    "strategy_checksum",
    "pair",
    "direction",
    "entry_ts",
    "entry_price",
    "risk_preset",
    "signal_meta",
    "outcome",
    "exit_ts",
    "exit_price",
    "pips",
    "outcome_meta",
    "recorded_at",
    "settled_at",
)


class LedgerError(ValueError):
    """A signal or outcome the ledger refuses to record, with the reasons."""


# --- Small parsing helpers --------------------------------------------------


def _parse_ts(value):
    """A timestamp as a datetime, or None when it isn't one. Accepts
    datetime instances and ISO-8601 strings (a trailing 'Z' is tolerated)."""
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return dt.datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _iso(value):
    """Normalised storage form of a timestamp already vetted by _parse_ts."""
    parsed = _parse_ts(value)
    return parsed.isoformat() if parsed is not None else None


def _naive_utc(parsed):
    """A datetime made comparable: aware values become naive UTC. Mixing
    aware and naive timestamps must never crash a comparison or a sort."""
    if parsed is not None and parsed.tzinfo is not None:
        return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _usable_number(value):
    """A float, or None when the value is not a usable number. Booleans and
    NaN are rejected explicitly, matching rforex.risk_presets._coerce."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _meta_json(meta, label, errors):
    """meta as a stored JSON string (or None), appending to errors when it
    cannot be represented."""
    if meta is None:
        return None
    if not isinstance(meta, dict):
        errors.append("{0} must be a dict when given.".format(label))
        return None
    try:
        return json.dumps(meta, sort_keys=True)
    except (TypeError, ValueError):
        errors.append("{0} must be JSON-serialisable.".format(label))
        return None


def _utcnow_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# --- Validation (all errors at once, like strategy_spec.validate_spec) ------


def validate_signal(strategy_id, strategy_checksum, pair, direction, entry_ts,
                    entry_price):
    """Every problem with a signal, as human-readable strings. Empty = ok."""
    errors = []
    if not isinstance(strategy_id, str) or not strategy_id.strip():
        errors.append("strategy_id must be a non-empty string (the "
                      "strategy's catalog identifier).")
    if not isinstance(strategy_checksum, str) or not strategy_checksum.strip():
        errors.append("strategy_checksum must be the pinned Forex Strategy "
                      "Version's spec_checksum — outcomes are only "
                      "meaningful per frozen parameter set.")
    if not isinstance(pair, str) or not pair.strip():
        errors.append("pair must be a non-empty string such as 'GBPUSD'.")
    if direction not in DIRECTIONS:
        errors.append("direction must be one of {0}; got {1!r}.".format(
            ", ".join(DIRECTIONS), direction))
    if _parse_ts(entry_ts) is None:
        errors.append("entry_ts must be a datetime or ISO-8601 string.")
    price = _usable_number(entry_price)
    if price is None or price <= 0:
        errors.append("entry_price must be a number greater than zero.")
    return errors


def validate_outcome(outcome, exit_ts, exit_price, pips, entry_ts=None):
    """Every problem with an outcome, as human-readable strings.

    `exit_price` may be None only for an expired signal — nothing was
    filled, so there is no exit. `pips` is required for every outcome
    (0 for expired/scratch is a real value, not a missing one) so the
    report never has to guess what a settled row was worth.
    """
    errors = []
    if outcome not in OUTCOMES:
        errors.append("outcome must be one of {0}; got {1!r}.".format(
            ", ".join(OUTCOMES), outcome))
    exit_parsed = _parse_ts(exit_ts)
    if exit_parsed is None:
        errors.append("exit_ts must be a datetime or ISO-8601 string.")
    entry_parsed = _parse_ts(entry_ts) if entry_ts is not None else None
    if (exit_parsed is not None and entry_parsed is not None
            and _naive_utc(exit_parsed) < _naive_utc(entry_parsed)):
        errors.append("exit_ts is earlier than the signal's entry_ts.")
    price = _usable_number(exit_price)
    if outcome == OUTCOME_EXPIRED:
        if exit_price is not None and (price is None or price <= 0):
            errors.append("exit_price must be a positive number or None "
                          "for an expired signal.")
    else:
        if price is None or price <= 0:
            errors.append("exit_price must be a number greater than zero.")
    if _usable_number(pips) is None:
        errors.append("pips must be a number (negative for a loss, 0 for a "
                      "scratch or an expiry).")
    return errors


# --- Storage: frappe DocType when composed, in-memory otherwise -------------

#: the in-memory fallback store. A dict keyed by signal_id so tests (and any
#: offline harness run) exercise exactly the same rules with no site.
_MEMORY = {}
_MEMORY_SEQ = [0]


def reset_memory_store():
    """Empty the in-memory store. Test/offline use only."""
    _MEMORY.clear()
    _MEMORY_SEQ[0] = 0


def _using_frappe():
    return frappe is not None and getattr(frappe, "db", None) is not None


def _memory_insert(row):
    _MEMORY_SEQ[0] += 1
    name = "FXSO-MEM-{0:05d}".format(_MEMORY_SEQ[0])
    row["name"] = name
    _MEMORY[name] = row
    return name


def _fetch(signal_id):
    """The stored row for signal_id as a plain dict, or None."""
    if _using_frappe():
        row = frappe.db.get_value(DOCTYPE, signal_id, list(FIELDS),
                                  as_dict=True)
        return dict(row) if row else None
    row = _MEMORY.get(signal_id)
    return dict(row) if row else None


# --- The API ----------------------------------------------------------------


def record_signal(strategy_id, strategy_checksum, pair, direction, entry_ts,
                  entry_price, risk_preset=None, meta=None):
    """Log one emitted signal, unsettled, and return its signal_id.

    Called at emission time — before the outcome exists — so the ledger
    cannot be curated by only logging trades that worked out.
    """
    errors = validate_signal(strategy_id, strategy_checksum, pair, direction,
                             entry_ts, entry_price)
    meta_text = _meta_json(meta, "meta", errors)
    if errors:
        raise LedgerError("This signal cannot be recorded: "
                          + " ".join(errors))

    row = {
        "strategy_id": strategy_id.strip(),
        "strategy_checksum": strategy_checksum.strip(),
        "pair": pair.strip().upper(),
        "direction": direction,
        "entry_ts": _iso(entry_ts),
        "entry_price": float(entry_price),
        "risk_preset": (risk_preset.strip()
                        if isinstance(risk_preset, str) and risk_preset.strip()
                        else None),
        "signal_meta": meta_text,
        "outcome": None,
        "exit_ts": None,
        "exit_price": None,
        "pips": None,
        "outcome_meta": None,
        "recorded_at": _utcnow_iso(),
        "settled_at": None,
    }

    if _using_frappe():
        doc = frappe.get_doc(dict(row, doctype=DOCTYPE))
        doc.insert(ignore_permissions=True)
        return doc.name
    return _memory_insert(row)


def record_outcome(signal_id, exit_ts, exit_price, outcome, pips, meta=None):
    """Settle one signal with what actually happened. Returns the settled
    row. Refuses a second verdict — the ledger is append-once, never edited.
    """
    existing = _fetch(signal_id)
    if existing is None:
        raise LedgerError(
            "No signal {0!r} on the ledger. Outcomes attach to recorded "
            "signals only — a result without its emission is not "
            "evidence.".format(signal_id))
    if existing.get("outcome"):
        raise LedgerError(
            "Signal {0!r} is already settled as {1!r}. Verdicts are written "
            "once; a correction is a note in meta on a new row, never an "
            "edit.".format(signal_id, existing["outcome"]))

    errors = validate_outcome(outcome, exit_ts, exit_price, pips,
                              entry_ts=existing.get("entry_ts"))
    meta_text = _meta_json(meta, "meta", errors)
    if errors:
        raise LedgerError("This outcome cannot be recorded: "
                          + " ".join(errors))

    exit_number = _usable_number(exit_price)
    updates = {
        "outcome": outcome,
        "exit_ts": _iso(exit_ts),
        "exit_price": float(exit_number) if exit_number is not None else None,
        "pips": float(pips),
        "outcome_meta": meta_text,
        "settled_at": _utcnow_iso(),
    }

    if _using_frappe():
        doc = frappe.get_doc(DOCTYPE, signal_id)
        for key, value in updates.items():
            setattr(doc, key, value)
        doc.save(ignore_permissions=True)
    else:
        _MEMORY[signal_id].update(updates)
    return _fetch(signal_id)


def get_signal(signal_id):
    """One ledger row as a plain dict, or None."""
    return _fetch(signal_id)


def list_signals(strategy_id=None, strategy_checksum=None, pair=None,
                 outcome=None, settled=None):
    """Ledger rows as plain dicts, oldest entry first.

    Filters are ANDed; None means "don't filter on this". `settled` is a
    tri-state: True = settled rows only, False = open rows only, None = all.
    """
    if _using_frappe():
        filters = {}
        if strategy_id is not None:
            filters["strategy_id"] = strategy_id
        if strategy_checksum is not None:
            filters["strategy_checksum"] = strategy_checksum
        if pair is not None:
            filters["pair"] = pair.strip().upper()
        if outcome is not None:
            filters["outcome"] = outcome
        if settled is True and "outcome" not in filters:
            filters["outcome"] = ("in", list(OUTCOMES))
        elif settled is False:
            filters["outcome"] = ("is", "not set")
        rows = [dict(r) for r in frappe.get_all(
            DOCTYPE, filters=filters, fields=list(FIELDS),
            limit_page_length=0)]
    else:
        rows = []
        for row in _MEMORY.values():
            if strategy_id is not None and row["strategy_id"] != strategy_id:
                continue
            if (strategy_checksum is not None
                    and row["strategy_checksum"] != strategy_checksum):
                continue
            if pair is not None and row["pair"] != pair.strip().upper():
                continue
            if outcome is not None and row["outcome"] != outcome:
                continue
            if settled is True and not row["outcome"]:
                continue
            if settled is False and row["outcome"]:
                continue
            rows.append(dict(row))

    def _entry_key(row):
        parsed = _naive_utc(_parse_ts(row.get("entry_ts")))
        return (parsed is None,
                parsed or dt.datetime.min,
                row.get("name") or "")

    return sorted(rows, key=_entry_key)
