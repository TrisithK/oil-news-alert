"""Brent-impact taxonomy (spec §2).

The category base weights and typical directions here are the backbone of the analysis layer:
the LLM classifies each article into a category, and the deterministic importance score combines
the category weight with the model's magnitude/confidence and the source tier. Typical direction
is a *prior*, not a rule — the model still reads the specific article.
"""

from __future__ import annotations

from enum import StrEnum


class EventCategory(StrEnum):
    OPEC_SUPPLY = "opec_supply_decision"
    GEOPOLITICS = "geopolitics_conflict"
    SHIPPING_CHOKEPOINT = "shipping_chokepoint"
    SUPPLY_OUTAGE = "supply_outage"
    SANCTIONS = "sanctions_embargo"
    INVENTORY = "inventory_data"
    MACRO = "macro_monetary"
    DEMAND = "demand_signal"
    STRATEGIC_RESERVES = "strategic_reserves"
    PRODUCTION_EXPORTS = "production_exports"
    WEATHER = "weather"
    RUMOR = "rumor_opinion"
    OTHER = "other"


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


class Magnitude(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeHorizon(StrEnum):
    IMMEDIATE = "immediate"
    INTRADAY = "intraday"
    DAYS = "days"
    STRUCTURAL = "structural"


class Instrument(StrEnum):
    BRENT = "BRENT"
    WTI = "WTI"
    GASOIL = "GASOIL"
    TTF_GAS = "TTF_GAS"
    USD = "USD"


# category -> (base_weight, typical_direction). Source: spec §2 table.
CATEGORY_PROFILE: dict[EventCategory, tuple[float, Direction]] = {
    EventCategory.OPEC_SUPPLY: (0.90, Direction.BULLISH),  # cut bullish / hike bearish
    EventCategory.GEOPOLITICS: (0.85, Direction.BULLISH),
    EventCategory.SHIPPING_CHOKEPOINT: (0.85, Direction.BULLISH),
    EventCategory.SANCTIONS: (0.80, Direction.BULLISH),
    EventCategory.SUPPLY_OUTAGE: (0.75, Direction.BULLISH),
    EventCategory.INVENTORY: (0.70, Direction.NEUTRAL),  # surprise vs consensus drives sign
    EventCategory.MACRO: (0.60, Direction.BEARISH),
    EventCategory.DEMAND: (0.55, Direction.BEARISH),
    EventCategory.STRATEGIC_RESERVES: (0.55, Direction.BEARISH),
    EventCategory.PRODUCTION_EXPORTS: (0.55, Direction.BEARISH),
    EventCategory.WEATHER: (0.45, Direction.BULLISH),
    EventCategory.RUMOR: (0.20, Direction.UNCLEAR),
    EventCategory.OTHER: (0.15, Direction.UNCLEAR),
}

MAGNITUDE_MAP: dict[Magnitude, float] = {
    Magnitude.LOW: 0.33,
    Magnitude.MEDIUM: 0.66,
    Magnitude.HIGH: 1.0,
}

SOURCE_TIER_WEIGHT: dict[str, float] = {
    "wire": 1.0,
    "reputable": 0.8,
    "aggregator": 0.6,
    "blog_social": 0.4,
}


def category_base_weight(category: EventCategory) -> float:
    return CATEGORY_PROFILE.get(category, CATEGORY_PROFILE[EventCategory.OTHER])[0]


def category_typical_direction(category: EventCategory) -> Direction:
    return CATEGORY_PROFILE.get(category, CATEGORY_PROFILE[EventCategory.OTHER])[1]
