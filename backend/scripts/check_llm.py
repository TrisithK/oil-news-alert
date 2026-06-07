"""Verify the live Anthropic LLM wiring: `make llm-check`.

If ANTHROPIC_API_KEY is set, makes ONE cheap Haiku triage call on a sample headline and prints the
result, model, and token usage — the quickest way to confirm a newly-added key works end to end.
Otherwise it reports that the offline heuristic client is in use (no key, no spend).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import setup_logging
from worker.analyze.llm import AnthropicLLMClient, get_llm_client

SAMPLE = "Iran threatens to close the Strait of Hormuz after attacks on oil tankers"


def main() -> None:
    setup_logging()
    llm = get_llm_client(settings)

    if not isinstance(llm, AnthropicLLMClient):
        print(
            "ANTHROPIC_API_KEY is not set — the offline heuristic client is in use (no live LLM)."
        )
        print("Add ANTHROPIC_API_KEY to .env, then `make up` and re-run this check.")
        return

    print(f"Using AnthropicLLMClient (triage={llm.triage_model}, extract={llm.extract_model})")
    print(f"Sample headline: {SAMPLE!r}\n")
    try:
        triage, usage = llm.triage(title=SAMPLE, body=None)
    except Exception as exc:  # noqa: BLE001 — surface auth/network errors plainly
        print(f"LLM call FAILED: {type(exc).__name__}: {exc}")
        print("Check that the key is valid and has access to the pinned models.")
        return

    print(f"triage.is_relevant = {triage.is_relevant}   ({triage.reason})")
    print(f"tokens: prompt={usage.prompt_tokens} completion={usage.completion_tokens}")
    print("\nLLM wiring OK ✓  — run `make analyze` to classify with the real models.")


if __name__ == "__main__":
    main()
