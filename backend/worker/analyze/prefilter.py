"""Stage 1 — keyword prefilter (no LLM).

Drops obvious non-oil noise for free before any model is called, which is the first and
cheapest lever in the cost-control story (spec §6).
"""

from __future__ import annotations

import re

# Single-token cues; multi-word events (e.g. "Strait of Hormuz") are caught by "hormuz".
OIL_KEYWORDS: tuple[str, ...] = (
    "oil",
    "crude",
    "brent",
    "wti",
    "opec",
    "petroleum",
    "refinery",
    "refineries",
    "refining",
    "barrel",
    "barrels",
    "gasoil",
    "diesel",
    "distillate",
    "gasoline",
    "hormuz",
    "suez",
    "bosporus",
    "houthi",
    "tanker",
    "pipeline",
    "sanction",
    "sanctions",
    "embargo",
    "opec+",
    "eia",
    "inventories",
    "inventory",
    "stockpile",
    "spr",
    "rig",
    "drilling",
    "saudi",
    "aramco",
    "urals",
)

_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(k) for k in OIL_KEYWORDS) + r")(?!\w)", re.IGNORECASE
)


def passes_prefilter(title: str | None, body: str | None = None) -> bool:
    text = f"{title or ''} {body or ''}"
    return bool(_PATTERN.search(text))
