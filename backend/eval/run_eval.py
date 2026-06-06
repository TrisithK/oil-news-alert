"""Golden-set evaluation harness (spec §14): `python -m eval.run_eval` (used by `make eval`).

Reports relevance precision/recall/F1 and direction agreement, and lists disagreements. Runs
against whichever LLM client is configured — the offline heuristic client when no API key is set,
or the real Anthropic models when ANTHROPIC_API_KEY is present.

The honest framing: for a news->price system the meaningful metric is whether high-importance
alerts track realized Brent moves and false positives stay low. The MVP ships this harness and the
feedback loop; validation against realized volatility is the documented next step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.logging import setup_logging
from worker.analyze.llm import LLMClient, get_llm_client

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"


def load_golden_set(path: Path = GOLDEN_SET) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


@dataclass
class EvalReport:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    direction_total: int = 0
    direction_agree: int = 0
    disagreements: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def direction_agreement(self) -> float:
        return self.direction_agree / self.direction_total if self.direction_total else 0.0


def evaluate(llm: LLMClient, items: list[dict]) -> EvalReport:
    report = EvalReport()
    for item in items:
        title = item["title"]
        body = item.get("body")
        expected_relevant = bool(item.get("relevant", False))

        triage, _ = llm.triage(title=title, body=body)
        predicted_relevant = triage.is_relevant

        if predicted_relevant and expected_relevant:
            report.tp += 1
        elif predicted_relevant and not expected_relevant:
            report.fp += 1
        elif not predicted_relevant and expected_relevant:
            report.fn += 1
        else:
            report.tn += 1

        expected_direction = item.get("direction")
        if expected_relevant and predicted_relevant and expected_direction:
            signal, _, _ = llm.extract(title=title, body=body)
            if signal is not None:
                report.direction_total += 1
                predicted_direction = signal.expected_direction.value
                if predicted_direction == expected_direction:
                    report.direction_agree += 1
                else:
                    report.disagreements.append((title, expected_direction, predicted_direction))
    return report


def format_report(report: EvalReport, n_items: int, engine: str) -> str:
    lines = [
        "=" * 70,
        f"Golden-set evaluation  ({n_items} items, engine={engine})",
        "=" * 70,
        "Relevance:",
        f"  precision={report.precision:.2f}  recall={report.recall:.2f}  f1={report.f1:.2f}",
        f"  confusion: tp={report.tp} fp={report.fp} fn={report.fn} tn={report.tn}",
        "Direction (on items both judged relevant):",
        f"  agreement = {report.direction_agreement:.2f}  "
        f"({report.direction_agree}/{report.direction_total})",
    ]
    if report.disagreements:
        lines.append("Direction disagreements:")
        for title, expected, predicted in report.disagreements:
            lines.append(f"  - expected {expected:<8} got {predicted:<8} | {title[:60]}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> None:
    setup_logging()
    items = load_golden_set()
    llm = get_llm_client(settings)
    report = evaluate(llm, items)
    print(format_report(report, len(items), llm.extract_model))


if __name__ == "__main__":
    main()
