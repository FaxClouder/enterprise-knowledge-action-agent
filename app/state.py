from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.rag.schemas import RetrievedDocument


IntentType = Literal["knowledge_qa", "policy_qa", "sql_analysis", "meeting_summary", "general"]


class AgentOutput(TypedDict, total=False):
    """Final normalized response schema exposed by the project."""

    answer: str
    used_tools: list[str]
    used_skill: str | None
    used_memory: list[str]
    citations: list[str]
    confidence: float
    error: str | None


class AgentState(TypedDict, total=False):
    """Mutable graph state for LangGraph workflow."""

    messages: Annotated[list[AnyMessage], add_messages]
    input: str
    user_id: str
    thread_id: str

    intent: IntentType
    needs_retrieval: bool
    retrieval_query: str
    rewritten_query: str
    retrieval_attempts: int
    max_retrieval_attempts: int
    docs_relevant: bool
    retrieval_grade_reason: str

    retrieved_docs: list[RetrievedDocument]
    citations: list[str]

    loaded_skill: str | None
    skill_content: str | None

    long_term_memory: dict[str, Any] | None
    short_term_summary: str
    used_memory: list[str]

    tool_context: str
    mcp_context: str
    used_tools: list[str]

    draft_answer: str
    final_answer: str
    confidence: float
    output: AgentOutput
    error: str | None
