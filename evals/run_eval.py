from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from app.graph import run_query


def load_dataset(path: Path) -> list[dict]:
    """Load JSONL evaluation dataset."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _answer_correct(answer: str, expected_keywords: list[str]) -> bool:
    if not expected_keywords:
        return bool(answer.strip())
    a = answer.lower()
    return any(k.lower() in a for k in expected_keywords)


def evaluate_case(case: dict) -> dict:
    """Run one eval case and compute metric booleans."""
    output = run_query(
        case["query"],
        user_id=case.get("user_id", "eval_user"),
        thread_id=case.get("thread_id", "eval_thread"),
    )

    answer = str(output.get("answer", ""))
    used_tools = output.get("used_tools", []) or []
    used_skill = output.get("used_skill")
    citations = output.get("citations", []) or []

    expected_skill = case.get("expected_skill")
    expected_tool = case.get("expected_tool_path", "none")

    answer_correct = _answer_correct(answer, case.get("expected_keywords", []))
    citation_present = True if not case.get("requires_citation") else len(citations) > 0

    if expected_skill is None:
        expected_skill_selected = used_skill is None
    else:
        expected_skill_selected = used_skill == expected_skill

    if expected_tool == "none":
        expected_tool_path = True
    else:
        expected_tool_path = expected_tool in used_tools

    return {
        "id": case["id"],
        "query": case["query"],
        "answer": answer,
        "used_skill": used_skill,
        "used_tools": used_tools,
        "citations": citations,
        "answer_correct": answer_correct,
        "citation_present": citation_present,
        "expected_skill_selected": expected_skill_selected,
        "expected_tool_path": expected_tool_path,
    }


def summarize(results: list[dict]) -> dict:
    """Aggregate metric pass rates."""
    metrics = [
        "answer_correct",
        "citation_present",
        "expected_skill_selected",
        "expected_tool_path",
    ]
    summary = {}
    for metric in metrics:
        vals = [1.0 if item[metric] else 0.0 for item in results]
        summary[metric] = round(mean(vals), 3) if vals else 0.0

    summary["num_cases"] = len(results)
    summary["overall"] = round(mean(summary[m] for m in metrics), 3) if results else 0.0
    return summary


def main() -> None:
    """Run evaluation and output report."""
    parser = argparse.ArgumentParser(description="Run project baseline eval")
    parser.add_argument("--dataset", default="evals/dataset.jsonl")
    parser.add_argument("--output", default="evals/latest_report.json")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    cases = load_dataset(dataset_path)
    results = [evaluate_case(case) for case in cases]
    summary = summarize(results)
    report = {"summary": summary, "results": results}

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Eval Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
