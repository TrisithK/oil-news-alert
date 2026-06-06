from __future__ import annotations

from eval.run_eval import evaluate, load_golden_set
from worker.analyze.llm import HeuristicLLMClient


def test_golden_set_loads() -> None:
    items = load_golden_set()
    assert len(items) >= 30
    assert all("title" in item for item in items)


def test_eval_metrics_are_reasonable() -> None:
    items = load_golden_set()
    report = evaluate(HeuristicLLMClient(), items)

    # Every item lands in exactly one confusion bucket.
    assert report.tp + report.fp + report.fn + report.tn == len(items)

    # The heuristic baseline should do clearly better than chance on this curated set.
    assert report.precision >= 0.8
    assert report.recall >= 0.85
    assert report.direction_agreement >= 0.7
