"""System prompts and forced-tool schemas for the two LLM stages.

The system prompts embed the taxonomy and are identical across every article, so they are
marked for prompt caching by the Anthropic client (render order tools -> system -> messages;
the per-article text goes in the user turn, after the cached prefix). See spec §6.
"""

from __future__ import annotations

from app.core.taxonomy import Direction, EventCategory, Instrument, Magnitude, TimeHorizon


def _values(enum_cls: type) -> list[str]:
    return [e.value for e in enum_cls]


_CATEGORY_LINES = "\n".join(f"  - {c.value}" for c in EventCategory)

TRIAGE_SYSTEM = (
    "You are a triage filter for a crude-oil trading desk. Decide whether a news item is "
    "MATERIALLY relevant to crude oil / ICE Brent pricing — i.e. it could plausibly move the "
    "price. Oil supply, demand, OPEC+, geopolitics affecting oil flows, shipping chokepoints, "
    "sanctions on oil barrels, refinery/pipeline outages, inventories, and oil-relevant macro "
    "all count. General politics, sports, tech, and company news with no oil-price channel do "
    "not. Be decisive and lean toward excluding noise. Always call the relevance_triage tool."
)

EXTRACT_SYSTEM = (
    "You are an oil-markets analyst for a European trading desk. Extract a single structured "
    "trading signal from the article using the extract_oil_signal tool. Classify it into one of "
    "these event categories:\n"
    f"{_CATEGORY_LINES}\n\n"
    "Guidance:\n"
    "- expected_direction is the likely effect on ICE Brent (bullish = price up). For scheduled "
    "data (e.g. EIA inventories) the SURPRISE vs consensus drives the sign, not the raw level.\n"
    "- magnitude reflects how much this could move price; confidence is your certainty (0-1).\n"
    "- time_horizon: immediate (minutes/hours), intraday, days, or structural.\n"
    "- instruments_affected: tag BRENT first; add WTI/GASOIL/TTF_GAS/USD when relevant.\n"
    "- rationale must be grounded in the article; headline_summary is a one-liner for a trader.\n"
    "- set is_scheduled_data=true for routine scheduled releases (EIA/API stats, OPEC/IEA monthly "
    "reports, FOMC/ECB decisions). Down-weight rumor/opinion."
)

RELEVANCE_TRIAGE_TOOL: dict = {
    "name": "relevance_triage",
    "description": "Record whether the article materially affects crude oil / Brent pricing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_relevant": {"type": "boolean"},
            "reason": {"type": "string", "description": "one-line justification"},
        },
        "required": ["is_relevant", "reason"],
        "additionalProperties": False,
    },
}

EXTRACT_OIL_SIGNAL_TOOL: dict = {
    "name": "extract_oil_signal",
    "description": "Extract a structured oil trading signal from the article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_relevant": {"type": "boolean"},
            "event_category": {"type": "string", "enum": _values(EventCategory)},
            "instruments_affected": {
                "type": "array",
                "items": {"type": "string", "enum": _values(Instrument)},
            },
            "expected_direction": {"type": "string", "enum": _values(Direction)},
            "magnitude": {"type": "string", "enum": _values(Magnitude)},
            "confidence": {"type": "number", "description": "0.0 to 1.0"},
            "time_horizon": {"type": "string", "enum": _values(TimeHorizon)},
            "rationale": {"type": "string"},
            "headline_summary": {"type": "string"},
            "key_entities": {"type": "array", "items": {"type": "string"}},
            "is_scheduled_data": {"type": "boolean"},
        },
        "required": [
            "is_relevant",
            "event_category",
            "instruments_affected",
            "expected_direction",
            "magnitude",
            "confidence",
            "time_horizon",
            "rationale",
            "headline_summary",
            "key_entities",
            "is_scheduled_data",
        ],
        "additionalProperties": False,
    },
}


def article_user_content(title: str, body: str | None) -> str:
    body_text = (body or "").strip()
    if len(body_text) > 4000:
        body_text = body_text[:4000] + "…"
    return f"HEADLINE: {title}\n\nBODY:\n{body_text or '(no body text available)'}"
