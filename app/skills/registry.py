from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillMeta:
    """Declarative metadata used for skill routing and lazy loading."""

    name: str
    summary: str
    path: Path
    intents: set[str]
    keywords: set[str]


BASE_DIR = Path(__file__).resolve().parent

SKILLS: dict[str, SkillMeta] = {
    "policy_qa": SkillMeta(
        name="policy_qa",
        summary="Answer enterprise policy/compliance questions with strict citation and boundary checks.",
        path=BASE_DIR / "policy_qa" / "SKILL.md",
        intents={"policy_qa", "knowledge_qa"},
        keywords={"policy", "合规", "报销", "请假", "审批", "制度"},
    ),
    "sql_analysis": SkillMeta(
        name="sql_analysis",
        summary="Generate safe read-only SQL and explain assumptions from provided schema.",
        path=BASE_DIR / "sql_analysis" / "SKILL.md",
        intents={"sql_analysis"},
        keywords={"sql", "query", "select", "gmv", "表结构", "指标"},
    ),
    "meeting_summary": SkillMeta(
        name="meeting_summary",
        summary="Summarize meeting notes into decisions, risks, and action items.",
        path=BASE_DIR / "meeting_summary" / "SKILL.md",
        intents={"meeting_summary"},
        keywords={"meeting", "纪要", "总结", "action items", "会议"},
    ),
}


def list_skill_summaries() -> list[dict[str, str]]:
    """Return only lightweight skill cards for initial context."""
    return [{"name": s.name, "summary": s.summary} for s in SKILLS.values()]


def select_skill(query: str, intent: str) -> SkillMeta | None:
    """Choose one skill based on intent and keyword matching."""
    text = query.lower()
    for meta in SKILLS.values():
        if intent in meta.intents:
            if any(k.lower() in text for k in meta.keywords):
                return meta
            if intent in {"sql_analysis", "meeting_summary"}:
                return meta
    return None
