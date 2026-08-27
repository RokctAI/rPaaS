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

"""Server-rendered end-user copy for severe-weather warnings.

Single source of truth for every string a client shows: calm, human, concrete
about what to do; no probabilities, no meteorology jargon, no technical
detail (all of that stays in admin logs). Rendered server-side so every
client shows identical text; changing copy is a backend-only deploy.

LEGAL CONSTRAINT (South Africa: only the national weather service may issue
official severe-weather warnings): no END-USER-FACING string in this module
may use the word "warning" or official warning taxonomy (yellow/orange/red
levels, "warning issued"). Everything users see is heads-up possibility
phrasing ("flooding is possible", "heavy rain expected"). The machine-facing
severity enum ("heads_up" | "warning") is an internal identifier - clients
must render SEVERITY_LABELS / the rendered strings, never the enum value.

Severity enum (internal) and its user-facing label:
  advisory  neighbor-propagated soft notice (propagation.py; strictly below
            heads_up in prominence)        -> label "Worth knowing"
  heads_up  early notice        -> label "Heads-up"
  warning   stronger, act soon  -> label "Please take care"

Neighbor-advisory copy is rendered by propagation.render_advisory; render()
below serves advisory copy ONLY for the advisory-capped cold_front class
(cold_front.py). The detector's own copy surface stays heads_up/warning
only, and SEVERITY_WORDS deliberately excludes advisory so detector-driven
severity handling (tier mapping, push ranking) can never produce or act on
one.

Product surface (deliberate, defensible):
  flash_flood, flood        rain-driven flooding - full heads-up surface
  destructive_wind          tropical-cyclone / destructive wind - full surface
  tornado                   at most a soft heads-up line ("storms possible");
                            never escalated past heads_up.
  cold_front                routine "cool change" notice (cold_front.py) -
                            hard-capped at the advisory tier, never
                            heads_up/warning.
  upstream_flood            basin-routed river-rise notice (basin.py): heavy
                            rain UPSTREAM raising a downstream river signal,
                            days ahead, at places that may see no rain at
                            all - full advisory/heads_up/warning surface.
                            The copy must say plainly that the water is
                            coming down the river even in dry local weather.

This module is dependency-free (stdlib only) so the client-facing endpoint
never imports the numeric stack.
"""
from __future__ import annotations

#: CC-BY-4.0 attribution for Open-Meteo data - carried in every response and
#: rendered on every surface that displays a warning.
ATTRIBUTION = "Weather data by Open-Meteo.com"

DEFAULT_PLACE = "your area"

SEVERITY_WORDS = ("heads_up", "warning")

#: user-facing rendering of the internal severity enum - wording-based, never
#: an official warning level. Clients show these (or nothing), not the enum.
#: "advisory" (propagation.ADVISORY_LABEL mirrors this string) is served so
#: clients that learn the enum value get a server-rendered label; clients
#: that do not know "advisory" fail closed and render nothing.
SEVERITY_LABELS = {
    "advisory": "Worth knowing",
    "heads_up": "Heads-up",
    "warning": "Please take care",
}

#: event classes exposed to end users, and the highest severity word each may
#: carry. tornado is capped at heads_up (soft line only) by product decision.
#: cold_front is ROUTINE weather (cold_front.py): hard-capped at advisory -
#: it can never surface as heads_up or warning through any severity path.
CLASS_MAX_SEVERITY = {
    "flash_flood": "warning",
    "flood": "warning",
    "destructive_wind": "warning",
    "tornado": "heads_up",
    "cold_front": "advisory",
    "upstream_flood": "warning",
}

_HEADLINES = {
    ("flash_flood", "heads_up"): "Flash flooding possible near {place}",
    ("flash_flood", "warning"): "Flash flooding likely near {place}",
    ("flood", "heads_up"): "Flooding possible near {place}",
    ("flood", "warning"): "Flooding expected near {place}",
    ("destructive_wind", "heads_up"): "Very windy day ahead near {place}",
    ("destructive_wind", "warning"): "Damaging winds expected near {place}",
    ("tornado", "heads_up"): "Storms possible near {place}",
    ("cold_front", "advisory"): "A cool change near {place}",
    ("upstream_flood", "advisory"): "Rain far upriver from {place}",
    ("upstream_flood", "heads_up"): "River levels may rise near {place}",
    ("upstream_flood", "warning"): "Rising river water expected near {place}",
}

_MESSAGES = {
    ("flash_flood", "heads_up"): (
        "Heavy rain could cause fast-rising water around {place} in the next "
        "day or so. If you're near streams or low-lying roads, keep an eye out."
    ),
    ("flash_flood", "warning"): (
        "Flash flooding looks likely around {place} in the coming hours. "
        "Please avoid low bridges and flooded roads - even shallow moving "
        "water is dangerous."
    ),
    ("flood", "heads_up"): (
        "Rivers and low ground around {place} are getting very wet. Flooding "
        "is possible over the next few days."
    ),
    ("flood", "warning"): (
        "Flooding is expected around {place} in the next day or two. If stock "
        "or vehicles sit on low ground, now is a good time to move them up."
    ),
    ("destructive_wind", "heads_up"): (
        "It may get very windy around {place} tomorrow. Worth tying down "
        "anything loose outside."
    ),
    ("destructive_wind", "warning"): (
        "Damaging winds are expected around {place} within the next day. "
        "Secure loose items, park clear of trees, and be ready for possible "
        "power cuts."
    ),
    ("tornado", "heads_up"): (
        "Conditions around {place} could turn stormy and severe today. Keep "
        "an ear on local alerts."
    ),
    ("cold_front", "advisory"): (
        "A cool change is moving through {place}. Expect a noticeable "
        "temperature drop, a wind shift and gusty conditions for a while."
    ),
    ("upstream_flood", "advisory"): (
        "Heavy rain has been falling far upriver from {place}. River "
        "levels could rise over the coming days, even if it stays dry "
        "where you are."
    ),
    ("upstream_flood", "heads_up"): (
        "A lot of rain has fallen upstream of {place}, and that water is "
        "making its way down the river. Levels could rise noticeably over "
        "the next few days, even without rain where you are. If you are "
        "near the river or on low ground, keep an eye on the water."
    ),
    ("upstream_flood", "warning"): (
        "Very heavy rain upstream is sending a lot of water down the "
        "river toward {place}. The river could rise strongly over the "
        "coming days, even in dry local weather. Please move stock, "
        "vehicles and valuables off low ground near the river, and be "
        "ready to head for higher ground if the water comes up."
    ),
}

#: cold-front copy variants (cold_front.py chooses at the detection cell;
#: propagation.py mirrors them on projected advisories). The UNUSUAL variant
#: is for a frontal passage that is out of the ordinary for the cell - e.g.
#: a front penetrating deep into hot northern areas - selected by the
#: data-driven unusualness gate in cold_front.py. The rain sentence is
#: appended ONLY when the post-frontal moisture/precipitation signal in the
#: observed series supports it. Calm phrasing; never the word "warning".
COLD_FRONT_UNUSUAL_HEADLINE = "Unusually cold change moving into {place}"
COLD_FRONT_UNUSUAL_MESSAGE = (
    "Noticeably colder weather is moving in around {place} - unusual for "
    "this area at this time of year. Expect a sharp temperature drop and "
    "gusty conditions."
)
COLD_FRONT_RAIN_SENTENCE = "Some rain may follow."

# --------------------------------------------------------------------------- #
# vulnerable-site notices (control/warnings_engine/sites.py, sw6)
#
# Disaster-management orgs think in named physical assets - a school, a
# clinic, a low-water bridge, a river crossing - not in coordinates. A
# Weather Vulnerable Site row names such an asset; when a heads-up becomes
# active for the asset's grid cell, render_site_notice() produces the one
# calm, site-specific line attached to it. Same legal constraint as every
# other string here: possibility phrasing only, never the word "warning" or
# official warning taxonomy.
# --------------------------------------------------------------------------- #

#: site types the Weather Vulnerable Site registry accepts.
SITE_TYPES = ("School", "Clinic", "Bridge", "River Crossing", "Other")

#: site types whose notices talk about passability (can you get across?);
#: every other type gets access/planning phrasing (can you get there?).
PASSABILITY_SITE_TYPES = ("Bridge", "River Crossing")

#: event class -> site-copy family. cold_front is deliberately absent: a
#: routine cool change never generates site notices (render_site_notice
#: raises KeyError - callers treat that as "do not surface").
SITE_CLASS_FAMILY = {
    "flash_flood": "flood",
    "flood": "flood",
    "upstream_flood": "flood",
    "destructive_wind": "wind",
    "tornado": "storm",
}

_SITE_HEADLINES = {
    ("flood", "passability", "heads_up"): "{site} may be hard to cross",
    ("flood", "passability", "warning"): "{site} may not be passable",
    ("flood", "access", "heads_up"): "Access to {site} may be affected",
    ("flood", "access", "warning"): "Reaching {site} may be difficult",
    ("wind", "passability", "heads_up"): "Windy conditions at {site}",
    ("wind", "passability", "warning"): "Strong winds expected at {site}",
    ("wind", "access", "heads_up"): "Windy conditions near {site}",
    ("wind", "access", "warning"): "Strong winds expected near {site}",
    ("storm", "passability", "heads_up"): "Storms possible near {site}",
    ("storm", "access", "heads_up"): "Storms possible near {site}",
}

_SITE_MESSAGES = {
    ("flood", "passability", "heads_up"): (
        "Flooding is possible in this area. The water at {site} could come "
        "up quickly - please check conditions before you cross."
    ),
    ("flood", "passability", "warning"): (
        "Flooding is expected in this area, and {site} is likely to become "
        "unusable while the water is up. Please plan another route and "
        "never cross moving water."
    ),
    ("flood", "access", "heads_up"): (
        "Flooding is possible in this area. Roads around {site} could be "
        "affected - worth planning ahead."
    ),
    ("flood", "access", "warning"): (
        "Flooding is expected in this area. Roads to and from {site} may "
        "become unusable - please plan ahead and allow extra time."
    ),
    ("wind", "passability", "heads_up"): (
        "It may get very windy in this area. Take extra care at {site}, "
        "especially in high-sided vehicles."
    ),
    ("wind", "passability", "warning"): (
        "Damaging winds are expected in this area. If you can, avoid "
        "crossing at {site} until the wind eases."
    ),
    ("wind", "access", "heads_up"): (
        "It may get very windy in this area. Loose items and temporary "
        "structures around {site} are worth securing."
    ),
    ("wind", "access", "warning"): (
        "Damaging winds are expected in this area. Plans and activities at "
        "{site} may be disrupted - please plan ahead."
    ),
    ("storm", "passability", "heads_up"): (
        "Storms are possible in this area today. Conditions at {site} could "
        "change quickly - please check before you travel."
    ),
    ("storm", "access", "heads_up"): (
        "Storms are possible in this area today. Worth keeping an eye on "
        "plans involving {site}."
    ),
}


def render_site_notice(event_class: str, severity: str, site_name: str,
                       site_type: str, route_label: str | None = None) -> dict:
    """Render the calm per-site line for one heads-up at one registered site.

    Returns {kind, severity, severity_label, headline, message, site_name,
    site_type} - kind is always "site_notice", the marker clients use to
    tell a site notice from a plain cell heads-up.

    Raises KeyError for any (event class, severity) pair without approved
    site copy - callers treat that as "do not surface". That covers
    cold_front (routine weather never names assets) and the advisory tier
    (site notices exist at heads_up and above only). Severity is clamped by
    the same per-class caps as render(), so tornado site notices can never
    exceed the soft heads_up line.
    """
    family = SITE_CLASS_FAMILY[event_class]  # KeyError = do not surface
    severity = cap_severity(event_class, severity)
    if severity not in SEVERITY_WORDS:
        raise KeyError((event_class, severity))
    group = ("passability" if site_type in PASSABILITY_SITE_TYPES
             else "access")
    site = (site_name or "").strip() or "this site"
    route = (route_label or "").strip()
    if route:
        site = f"{site} ({route})"
    key = (family, group, severity)
    return {
        "kind": "site_notice",
        "severity": severity,
        "severity_label": SEVERITY_LABELS[severity],
        "headline": _SITE_HEADLINES[key].format(site=site),
        "message": _SITE_MESSAGES[key].format(site=site),
        "site_name": site_name,
        "site_type": site_type,
    }


#: SMS budget for the fallback channel (one classic segment). The trimmer
#: only ever REMOVES words from already-approved copy - it can never
#: introduce a banned one.
SMS_MAX_CHARS = 160

#: escalation SMS may run to two segments: the acknowledge link must fit.
ESCALATION_SMS_MAX_CHARS = 320

#: contact-facing escalation copy (staff, but the same legal rule applies:
#: calm phrasing, never the word the national weather service owns).
ESCALATION_NOTE = ("No one has confirmed they have seen this notice yet. "
                   "Please make sure someone is looking into it.")
ESCALATION_ACK_PROMPT = "Confirm it is being handled here: {link}"


def _squash(text) -> str:
    """Collapse whitespace; None-safe."""
    return " ".join(str(text or "").split())


def _trim_to(text: str, limit: int) -> str:
    """Word-boundary trim with an ellipsis; removal-only."""
    if len(text) <= limit:
        return text
    cut = text[: max(limit - 3, 0)]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:!") + "..."


def sms_text(headline: str, message: str = "") -> str:
    """One SMS-sized string from already-rendered calm copy.

    Input is the server-rendered headline/message pair (render() above, or
    the same strings as served by the warnings API); output is headline plus
    as much of the message as fits in SMS_MAX_CHARS, trimmed at a word
    boundary. Removal-only: no new words, so the SAWS copy rules hold by
    construction.
    """
    headline, message = _squash(headline), _squash(message)
    text = headline or message
    if headline and message:
        room = SMS_MAX_CHARS - len(headline) - 1
        if len(message) <= room:
            text = headline + " " + message
        elif room >= 24:  # only append a fragment when it stays meaningful
            text = headline + " " + _trim_to(message, room)
    return _trim_to(text, SMS_MAX_CHARS)


def render_escalation(headline: str, message: str, ack_url=None) -> dict:
    """{subject, body} for one human escalation step (push title/body and
    email subject/message share it). The acknowledge link is appended only
    when the caller could build one."""
    headline, message = _squash(headline), _squash(message)
    parts = [part for part in (message, ESCALATION_NOTE) if part]
    if ack_url:
        parts.append(ESCALATION_ACK_PROMPT.format(link=ack_url))
    return {"subject": headline, "body": " ".join(parts)}


def escalation_sms_text(headline: str, ack_url=None) -> str:
    """SMS variant of one escalation step: trimmed headline plus the
    acknowledge link when it fits the two-segment budget."""
    text = _trim_to(_squash(headline), SMS_MAX_CHARS)
    link = _squash(ack_url)
    if link and len(text) + 1 + len(link) <= ESCALATION_SMS_MAX_CHARS:
        text = text + " " + link
    return text


def cap_severity(event_class: str, severity: str) -> str:
    """Clamp a severity word to what this class is allowed to show.

    "advisory" passes through unchanged: it sits strictly BELOW every
    per-class cap, so clamping can never raise it to heads_up. (Detector
    paths never produce it - it exists only on records owned by the
    propagation and cold-front passes.)

    A class whose CLASS_MAX_SEVERITY is "advisory" (cold_front) is ALWAYS
    clamped to advisory - the informational hard cap: no caller, whatever
    word it passes, can surface such a class above advisory prominence.
    """
    if CLASS_MAX_SEVERITY.get(event_class) == "advisory":
        return "advisory"
    if severity == "advisory":
        return "advisory"
    if CLASS_MAX_SEVERITY.get(event_class) == "heads_up":
        return "heads_up"
    return severity if severity in SEVERITY_WORDS else "heads_up"


def render(event_class: str, severity: str, place: str | None = None) -> dict:
    """Render {severity, severity_label, headline, message} for one heads-up.

    Raises KeyError for an event class / severity pair that has no approved
    copy - callers treat that as "do not surface". No returned user-facing
    string ever contains the word "warning" or an official warning level.
    """
    place = (place or "").strip() or DEFAULT_PLACE
    severity = cap_severity(event_class, severity)
    key = (event_class, severity)
    return {
        "severity": severity,
        "severity_label": SEVERITY_LABELS[severity],
        "headline": _HEADLINES[key].format(place=place),
        "message": _MESSAGES[key].format(place=place),
    }
