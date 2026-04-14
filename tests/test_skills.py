from __future__ import annotations

from app.skills.loader import load_skill_for_query
from app.skills.registry import list_skill_summaries, select_skill


def test_skill_registry_cards() -> None:
    cards = list_skill_summaries()
    assert len(cards) >= 3


def test_select_sql_skill() -> None:
    skill = select_skill("帮我生成 SQL 查询", "sql_analysis")
    assert skill is not None
    assert skill.name == "sql_analysis"


def test_lazy_load_skill() -> None:
    name, content = load_skill_for_query("请总结会议纪要", "meeting_summary")
    assert name == "meeting_summary"
    assert "Applicable Scenarios" in (content or "")
