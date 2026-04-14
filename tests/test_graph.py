from __future__ import annotations

from app.graph import route_intent, decide_retrieval, load_skill


def test_route_intent_sql() -> None:
    state = route_intent({"input": "请帮我写一个查询GMV的SQL"})
    assert state["intent"] == "sql_analysis"


def test_decide_retrieval_policy() -> None:
    state = decide_retrieval({"intent": "policy_qa", "input": "请问差旅报销政策"})
    assert state["needs_retrieval"] is True


def test_load_skill_meeting() -> None:
    state = load_skill({"intent": "meeting_summary", "input": "帮我总结会议纪要"})
    assert state["loaded_skill"] == "meeting_summary"
