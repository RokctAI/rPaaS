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

"""Frozen-parameters and holdout-era guards — frappe-free pure module.

Where the parameters live: **in the existing checksummed catalog, and only
there.** A strategy's thresholds are the spec inside its `Forex Strategy
Version` row, frozen by that DocType the moment the version leaves draft
and identified by the SHA-256 of the canonicalised spec. This module adds
no second copy of any parameter — it adds the two refusals that keep the
retraining loop honest, ported from the zones retraining harness:

1. **FrozenConfigError** — any path that would change what a non-draft
   version means must be refused. Retuning produces a NEW version (new
   number, new checksum, opted into by users), never a mutation. The
   DocType already enforces this on the desk; `guard_spec_mutation` is the
   same refusal for offline tools and harnesses that handle spec dicts
   directly, so "it wasn't going through frappe" is never an excuse.

2. **HoldoutAccessError** — backtest data is split into a tuning era and a
   holdout era, and tuning code that reads holdout data is refused at the
   read, not trusted to abstain. Tune on era A, prove on era B — once. A
   holdout that has been read during tuning, or evaluated twice, has been
   spent: its results stop being evidence, because the candidate has
   partly memorised the answers. See forex/BACKTEST.md for the protocol
   these guards enforce.

Nothing here is a policy knob. Loosening either guard IS the failure mode
this module exists to prevent.
"""

import datetime as dt
import hashlib
import json

#: the one non-draft-editable status, mirrored from
#: rforex.strategy_spec._EDITABLE_STATUSES (tenant side). Restated here as
#: a single string rather than imported because the control plane composes
#: without the tenant package; test_frozen_guards pins the two in sync
#: against the tenant module loaded by path.
EDITABLE_STATUS = "draft"


class FrozenConfigError(RuntimeError):
    """Refusal to change what a published strategy version means.

    The only sanctioned change is a NEW `Forex Strategy Version` with its
    own number and checksum, published through the catalog and opted into
    by users. There is deliberately no override flag.
    """


class HoldoutAccessError(RuntimeError):
    """Refusal to read holdout-era data during tuning, or to evaluate the
    holdout more than once. A spent holdout is spent forever."""


def _canonical(spec):
    """Key-sorted, whitespace-free JSON. The SAME canonicalisation as
    forex_strategy_version._canonical (that module imports frappe and
    cannot be loaded here); test_frozen_guards pins the two byte-for-byte
    so they cannot drift apart silently."""
    return json.dumps(spec, sort_keys=True, separators=(",", ":"))


def spec_checksum(spec):
    """The catalog identity of a spec: SHA-256 over its canonical form —
    a function of the spec's meaning, not of its formatting."""
    return hashlib.sha256(_canonical(spec).encode("utf-8")).hexdigest()


def guard_spec_mutation(status, stored_checksum, proposed_spec):
    """Refuse any change to a non-draft version's spec. Returns the
    proposed spec's checksum when the write is permissible.

    status: the version's catalog status. Anything other than `draft`
    (including None, unknown strings, and every published/retired/blocked
    state) is treated as frozen — fail closed, exactly like the DocType.
    stored_checksum: the catalog's recorded spec_checksum for the version.
    proposed_spec: the spec dict about to be written.

    A reformat is not a change: if the proposed spec canonicalises to the
    stored checksum, the write is a no-op and passes.
    """
    proposed = spec_checksum(proposed_spec)
    if status == EDITABLE_STATUS:
        return proposed
    if stored_checksum and proposed != stored_checksum:
        raise FrozenConfigError(
            "This version is {0!r} and its parameters are frozen "
            "(checksum {1}). Retuning means publishing a NEW strategy "
            "version — users move to it by choice; nothing mutates a spec "
            "somebody's money may be running.".format(
                status, stored_checksum))
    if not stored_checksum:
        # A frozen version with no recorded checksum is a corrupt row, not
        # a licence to write. Refuse and say why.
        raise FrozenConfigError(
            "This version is {0!r} but carries no spec_checksum to compare "
            "against; refusing the write rather than guessing it is "
            "unchanged.".format(status))
    return proposed


def _parse_ts(value):
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, dt.date):
        parsed = dt.datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError:
            raise HoldoutAccessError(
                "Unparseable timestamp {0!r} at an era boundary or read — "
                "refused rather than guessed onto one side of the "
                "split.".format(value))
    else:
        raise HoldoutAccessError(
            "Unparseable timestamp {0!r} at an era boundary or read — "
            "refused rather than guessed onto one side of the "
            "split.".format(value))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


class BacktestEraGuard:
    """The era discipline as an object the data loader must go through.

    tune era  [tune_start, tune_end)   — search, fit, iterate freely.
    holdout   [holdout_start, holdout_end) — read ONCE, blind, after the
              candidate is final.

    Construction refuses overlapping or misordered eras (the tune era must
    end at or before the holdout begins — proving a candidate on time it
    has already seen proves nothing). During tuning every read is checked
    by assert_tuning_read; the holdout is unlocked by begin_holdout_
    evaluation, exactly once, and stays spent for the life of the guard.
    Nothing un-spends it — if the holdout result disappoints, the answer
    is a new candidate and a NEW holdout era going forward in time, not a
    second look (see forex/BACKTEST.md).
    """

    def __init__(self, tune_start, tune_end, holdout_start, holdout_end):
        self.tune_start = _parse_ts(tune_start)
        self.tune_end = _parse_ts(tune_end)
        self.holdout_start = _parse_ts(holdout_start)
        self.holdout_end = _parse_ts(holdout_end)
        if not (self.tune_start < self.tune_end
                and self.holdout_start < self.holdout_end):
            raise HoldoutAccessError(
                "Each era must run forwards: start strictly before end.")
        if self.tune_end > self.holdout_start:
            raise HoldoutAccessError(
                "HOLDOUT GUARD: the tuning era ({0}..{1}) reaches into the "
                "holdout era ({2}..{3}). The whole point is proving the "
                "candidate on time it never saw.".format(
                    self.tune_start.date(), self.tune_end.date(),
                    self.holdout_start.date(), self.holdout_end.date()))
        self._holdout_spent = False

    @property
    def holdout_spent(self):
        return self._holdout_spent

    def assert_tuning_read(self, ts):
        """Called by the data path for every record read while tuning.
        Raises HoldoutAccessError on any timestamp at or past the holdout
        boundary; also refuses reads outside the declared tune era, so a
        'pre-era warm-up peek' cannot smuggle data in from either side."""
        parsed = _parse_ts(ts)
        if parsed >= self.holdout_start:
            raise HoldoutAccessError(
                "HOLDOUT GUARD: tuning tried to read {0}, inside the "
                "holdout era starting {1}. Tuning never touches holdout "
                "data — that is the only reason the holdout result will "
                "mean anything.".format(parsed.isoformat(),
                                        self.holdout_start.date()))
        if not (self.tune_start <= parsed < self.tune_end):
            raise HoldoutAccessError(
                "Tuning tried to read {0}, outside the declared tuning era "
                "{1}..{2}. Eras are declared before the run and every read "
                "stays inside them.".format(parsed.isoformat(),
                                            self.tune_start.date(),
                                            self.tune_end.date()))
        return parsed

    def begin_holdout_evaluation(self):
        """Unlock the single blind read of the holdout era. The second call
        — any second call, ever, on this guard — raises: a re-run against
        data whose answers have been seen is not evidence."""
        if self._holdout_spent:
            raise HoldoutAccessError(
                "HOLDOUT GUARD: this holdout era ({0}..{1}) has already "
                "been evaluated and is SPENT. Its result stands as "
                "reported; re-running against it can only launder a "
                "worse candidate.".format(self.holdout_start.date(),
                                          self.holdout_end.date()))
        self._holdout_spent = True
        return {
            "holdout_start": self.holdout_start.isoformat(),
            "holdout_end": self.holdout_end.isoformat(),
            "spent_at": dt.datetime.now(dt.timezone.utc).replace(
                microsecond=0).isoformat(),
        }

    def assert_holdout_read(self, ts):
        """Called by the data path during the (single) holdout evaluation.
        Requires begin_holdout_evaluation to have been called and the
        timestamp to sit inside the holdout era."""
        if not self._holdout_spent:
            raise HoldoutAccessError(
                "Holdout read before begin_holdout_evaluation(): the "
                "single evaluation must be declared before any holdout "
                "data is read, so a 'quick look' cannot precede it.")
        parsed = _parse_ts(ts)
        if not (self.holdout_start <= parsed < self.holdout_end):
            raise HoldoutAccessError(
                "Holdout evaluation tried to read {0}, outside the holdout "
                "era {1}..{2}.".format(parsed.isoformat(),
                                       self.holdout_start.date(),
                                       self.holdout_end.date()))
        return parsed
