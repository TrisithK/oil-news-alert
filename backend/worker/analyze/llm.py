"""The LLM layer behind one swappable interface (spec §4, §6).

- ``AnthropicLLMClient`` — the real two-tier client: Haiku for cheap relevance triage, Sonnet
  for structured signal extraction via a FORCED ``extract_oil_signal`` tool call, validated with
  Pydantic (repair-or-discard). System prompts are marked for prompt caching.
- ``HeuristicLLMClient`` — a deterministic, keyword-rule stand-in used when no ANTHROPIC_API_KEY
  is set and in tests. Makes the whole pipeline + eval run offline at zero API cost.

``get_llm_client`` picks the real client when a key is present, else the heuristic one.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.taxonomy import (
    Direction,
    EventCategory,
    Instrument,
    Magnitude,
    TimeHorizon,
)
from worker.analyze.prefilter import passes_prefilter
from worker.analyze.prompts import (
    EXTRACT_OIL_SIGNAL_TOOL,
    EXTRACT_SYSTEM,
    RELEVANCE_TRIAGE_TOOL,
    TRIAGE_SYSTEM,
    article_user_content,
)
from worker.analyze.schema import OilSignal, TriageResult

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
        )


class LLMClient(ABC):
    triage_model: str
    extract_model: str

    @abstractmethod
    def triage(self, *, title: str, body: str | None) -> tuple[TriageResult, TokenUsage]: ...

    @abstractmethod
    def extract(
        self, *, title: str, body: str | None
    ) -> tuple[OilSignal | None, TokenUsage, str | None]:
        """Return (signal, usage, discard_reason). signal is None iff extraction was discarded."""


# --------------------------------------------------------------------------------------
# Real client
# --------------------------------------------------------------------------------------
class AnthropicLLMClient(LLMClient):
    def __init__(self, settings: Settings = default_settings) -> None:
        import anthropic  # imported lazily so the heuristic path needs no dependency

        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, max_retries=2, timeout=30.0
        )
        self.triage_model = settings.triage_model
        self.extract_model = settings.extract_model

    @staticmethod
    def _usage(resp: object) -> TokenUsage:
        u = getattr(resp, "usage", None)
        if u is None:
            return TokenUsage()
        prompt = (
            (getattr(u, "input_tokens", 0) or 0)
            + (getattr(u, "cache_read_input_tokens", 0) or 0)
            + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        )
        return TokenUsage(prompt, getattr(u, "output_tokens", 0) or 0)

    @staticmethod
    def _tool_input(resp: object, tool_name: str) -> dict | None:
        for block in getattr(resp, "content", []) or []:
            if (
                getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", None) == tool_name
            ):
                return dict(block.input)
        return None

    def triage(self, *, title: str, body: str | None) -> tuple[TriageResult, TokenUsage]:
        resp = self.client.messages.create(
            model=self.triage_model,
            max_tokens=256,
            system=[
                {"type": "text", "text": TRIAGE_SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[RELEVANCE_TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "relevance_triage"},
            messages=[{"role": "user", "content": article_user_content(title, body)}],
        )
        usage = self._usage(resp)
        data = self._tool_input(resp, "relevance_triage") or {}
        try:
            return TriageResult.model_validate(data), usage
        except ValidationError:
            return TriageResult(is_relevant=False, reason="triage output unparseable"), usage

    def _extract_once(self, user_content: str) -> tuple[dict | None, TokenUsage]:
        resp = self.client.messages.create(
            model=self.extract_model,
            max_tokens=1024,
            system=[
                {"type": "text", "text": EXTRACT_SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[EXTRACT_OIL_SIGNAL_TOOL],
            tool_choice={"type": "tool", "name": "extract_oil_signal"},
            messages=[{"role": "user", "content": user_content}],
        )
        return self._tool_input(resp, "extract_oil_signal"), self._usage(resp)

    def extract(
        self, *, title: str, body: str | None
    ) -> tuple[OilSignal | None, TokenUsage, str | None]:
        user = article_user_content(title, body)
        data, usage = self._extract_once(user)
        err = "no tool_use block returned" if data is None else None
        if data is not None:
            try:
                return OilSignal.model_validate(data), usage, None
            except ValidationError as e:
                err = str(e)

        # One repair attempt: re-ask with the validation error appended (repair-or-discard).
        repair_user = (
            f"{user}\n\nIMPORTANT: your previous extract_oil_signal output was invalid ({err}). "
            "Call extract_oil_signal again with valid values for EVERY required field."
        )
        try:
            data2, usage2 = self._extract_once(repair_user)
        except Exception as exc:  # noqa: BLE001 — surface as a discard, don't crash the cycle
            return None, usage, f"repair call failed: {exc}"
        usage = usage + usage2
        try:
            return OilSignal.model_validate(data2 or {}), usage, None
        except ValidationError as e2:
            return None, usage, f"schema validation failed after repair: {e2}"


# --------------------------------------------------------------------------------------
# Deterministic offline stand-in
# --------------------------------------------------------------------------------------
_RULES: list[tuple[str, EventCategory, Direction | None, Magnitude]] = [
    (
        r"hormuz|strait|red sea|suez|bosporus|houthi|tanker|chokepoint|blockad",
        EventCategory.SHIPPING_CHOKEPOINT,
        Direction.BULLISH,
        Magnitude.HIGH,
    ),
    (r"\bopec\b|opec\+", EventCategory.OPEC_SUPPLY, None, Magnitude.HIGH),
    (r"sanction|embargo|\bban\b|price cap", EventCategory.SANCTIONS, None, Magnitude.HIGH),
    (
        r"refinery|refineries|refining|outage|force majeure|pipeline|platform|"
        r"wildfire|hurricane|shutdown|\bfire\b",
        EventCategory.SUPPLY_OUTAGE,
        Direction.BULLISH,
        Magnitude.MEDIUM,
    ),
    (
        r"ceasefire|de-escalat|truce|peace deal|peace talks",
        EventCategory.GEOPOLITICS,
        Direction.BEARISH,
        Magnitude.MEDIUM,
    ),
    (
        r"\bwar\b|attack|strike|missile|drone|conflict|escalat|invasion|tension|retaliat",
        EventCategory.GEOPOLITICS,
        Direction.BULLISH,
        Magnitude.HIGH,
    ),
    (
        r"inventor|stocks|stockpile|\beia\b|\bapi\b|drawdown|\bdraw\b|\bbuild\b",
        EventCategory.INVENTORY,
        None,
        Magnitude.MEDIUM,
    ),
    (
        r"\bfed\b|\becb\b|fomc|interest rate|rate hike|rate cut|\bcpi\b|"
        r"inflation|recession|monetary|dollar",
        EventCategory.MACRO,
        None,
        Magnitude.MEDIUM,
    ),
    (
        r"china|demand|\bpmi\b|imports|\biea\b|consumption",
        EventCategory.DEMAND,
        None,
        Magnitude.MEDIUM,
    ),
    (
        r"\bspr\b|strategic petroleum reserve|strategic reserve|reserve release|refill",
        EventCategory.STRATEGIC_RESERVES,
        None,
        Magnitude.MEDIUM,
    ),
    (
        r"rig count|exports|production|output|barrels per day|\bbpd\b|drilling",
        EventCategory.PRODUCTION_EXPORTS,
        None,
        Magnitude.MEDIUM,
    ),
    (
        r"cold snap|heating|freeze|blizzard|snowstorm|weather",
        EventCategory.WEATHER,
        Direction.BULLISH,
        Magnitude.LOW,
    ),
    (
        r"analyst|forecast|note|rumor|rumour|speculat",
        EventCategory.RUMOR,
        Direction.UNCLEAR,
        Magnitude.LOW,
    ),
]

_HORIZON: dict[EventCategory, TimeHorizon] = {
    EventCategory.SHIPPING_CHOKEPOINT: TimeHorizon.IMMEDIATE,
    EventCategory.GEOPOLITICS: TimeHorizon.IMMEDIATE,
    EventCategory.SUPPLY_OUTAGE: TimeHorizon.IMMEDIATE,
    EventCategory.INVENTORY: TimeHorizon.INTRADAY,
    EventCategory.MACRO: TimeHorizon.INTRADAY,
    EventCategory.OPEC_SUPPLY: TimeHorizon.DAYS,
    EventCategory.SANCTIONS: TimeHorizon.STRUCTURAL,
}


def _resolve_direction(category: EventCategory, text: str) -> Direction:
    bull = lambda p: re.search(p, text) is not None  # noqa: E731
    if category is EventCategory.OPEC_SUPPLY:
        if bull(r"cut|reduce|curb|trim|voluntary|extend"):
            return Direction.BULLISH
        if bull(r"hike|raise|increase|boost|more|unwind|restore|ramp"):
            return Direction.BEARISH
        return Direction.UNCLEAR
    if category is EventCategory.SANCTIONS:
        return Direction.BEARISH if bull(r"eas|lift|waiver|relax|remov") else Direction.BULLISH
    if category is EventCategory.INVENTORY:
        if bull(r"draw|fell|declin|drop|fall"):
            return Direction.BULLISH
        if bull(r"build|rose|rise|surg|jump|climb"):
            return Direction.BEARISH
        return Direction.NEUTRAL
    if category is EventCategory.MACRO:
        return (
            Direction.BULLISH
            if bull(r"rate cut|dovish|stimulus|weaker dollar")
            else Direction.BEARISH
        )
    if category is EventCategory.DEMAND:
        return (
            Direction.BULLISH if bull(r"strong|rise|surg|record|robust|grow") else Direction.BEARISH
        )
    if category is EventCategory.STRATEGIC_RESERVES:
        return Direction.BULLISH if bull(r"refill|buy|replenish") else Direction.BEARISH
    if category is EventCategory.PRODUCTION_EXPORTS:
        return (
            Direction.BEARISH
            if bull(r"rise|increase|more|record|ramp|boost")
            else Direction.BULLISH
        )
    return Direction.UNCLEAR


def _instruments(text: str) -> list[Instrument]:
    out = [Instrument.BRENT]
    if re.search(r"\bwti\b|west texas", text):
        out.append(Instrument.WTI)
    if re.search(r"diesel|gasoil|distillate", text):
        out.append(Instrument.GASOIL)
    if re.search(r"natural gas|\bttf\b|\blng\b", text):
        out.append(Instrument.TTF_GAS)
    if re.search(r"dollar|\bfed\b|\becb\b", text):
        out.append(Instrument.USD)
    return out


def classify_heuristic(title: str, body: str | None) -> OilSignal:
    text = f"{title} {body or ''}".lower()
    category, direction, magnitude = EventCategory.OTHER, Direction.UNCLEAR, Magnitude.LOW
    for pattern, cat, fixed_dir, mag in _RULES:
        if re.search(pattern, text):
            category, direction, magnitude = cat, fixed_dir, mag
            break
    if direction is None:
        direction = _resolve_direction(category, text)

    is_scheduled = (
        category is EventCategory.INVENTORY and bool(re.search(r"\beia\b|\bapi\b|weekly", text))
    ) or (category is EventCategory.MACRO and bool(re.search(r"\bfed\b|\becb\b|fomc", text)))
    entities = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", title)[:5]
    return OilSignal(
        is_relevant=category is not EventCategory.OTHER,
        event_category=category,
        instruments_affected=_instruments(text),
        expected_direction=direction,
        magnitude=magnitude,
        confidence=0.55,
        time_horizon=_HORIZON.get(category, TimeHorizon.DAYS),
        rationale=f"Heuristic classifier matched {category.value} (offline mock; no LLM call).",
        headline_summary=title[:120],
        key_entities=entities,
        is_scheduled_data=is_scheduled,
    )


class HeuristicLLMClient(LLMClient):
    """Deterministic, no-network stand-in. Same interface as the real client."""

    def __init__(self, settings: Settings = default_settings) -> None:
        self.triage_model = "heuristic-mock"
        self.extract_model = "heuristic-mock"

    def triage(self, *, title: str, body: str | None) -> tuple[TriageResult, TokenUsage]:
        relevant = passes_prefilter(title, body)
        reason = "matched oil keywords" if relevant else "no oil keywords"
        return TriageResult(is_relevant=relevant, reason=reason), TokenUsage()

    def extract(
        self, *, title: str, body: str | None
    ) -> tuple[OilSignal | None, TokenUsage, str | None]:
        return classify_heuristic(title, body), TokenUsage(), None


def get_llm_client(settings: Settings = default_settings) -> LLMClient:
    if settings.anthropic_api_key:
        log.info(
            "Using AnthropicLLMClient (triage=%s, extract=%s).",
            settings.triage_model,
            settings.extract_model,
        )
        return AnthropicLLMClient(settings)
    log.warning("ANTHROPIC_API_KEY not set — using HeuristicLLMClient (offline, no API spend).")
    return HeuristicLLMClient(settings)
