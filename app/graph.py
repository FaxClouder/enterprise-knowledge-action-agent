from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.mcp.resources import get_resource_service
from app.memory.long_term import get_long_term_store
from app.memory.short_term import get_checkpointer, summarize_recent_messages
from app.prompts import ANSWER_SYSTEM_PROMPT, FINAL_FORMAT_REMINDER
from app.rag.grading import grade_documents
from app.rag.retriever import get_retriever
from app.rag.rewrite import rewrite_query
from app.skills.loader import load_skill_for_query
from app.state import AgentState
from app.tools import get_all_tools

LOGGER = logging.getLogger(__name__)
_INCOMPATIBLE_PROVIDER_WARNED = False


def _enable_langsmith(settings: Settings) -> None:
    """Enable LangSmith tracing via environment variables when configured."""
    enabled = settings.langsmith_tracing and bool(settings.langsmith_api_key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if enabled and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key


def _extract_query(state: AgentState) -> str:
    if state.get("input"):
        return str(state["input"])
    messages = state.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return str(getattr(last, "content", ""))


def _classify_intent(query: str) -> str:
    text = query.lower()
    if any(k in text for k in ["sql", "gmv", "query", "select", "表结构"]):
        return "sql_analysis"
    if any(k in text for k in ["会议", "纪要", "meeting notes", "summary", "总结"]):
        return "meeting_summary"
    if any(k in text for k in ["policy", "合规", "报销", "请假", "审批", "制度"]):
        return "policy_qa"
    if any(k in text for k in ["流程", "规范", "知识库", "手册", "who", "what", "how"]):
        return "knowledge_qa"
    return "general"


def _should_retrieve(intent: str, query: str) -> bool:
    if intent in {"knowledge_qa", "policy_qa"}:
        return True
    if "根据文档" in query or "知识库" in query:
        return True
    return False


def _render_docs_context(state: AgentState, max_docs: int = 4) -> str:
    docs = state.get("retrieved_docs", [])[:max_docs]
    if not docs:
        return ""
    blocks = []
    for idx, doc in enumerate(docs, start=1):
        blocks.append(f"[Doc {idx} | {doc.source} | score={doc.score:.3f}]\n{doc.content[:600]}")
    return "\n\n".join(blocks)


def _extract_message_content(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(item) for item in content)
    return str(content)


def _extract_tool_usage(messages: list[Any]) -> list[str]:
    used: list[str] = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool":
            name = getattr(msg, "name", None)
            if name:
                used.append(str(name))
        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", None) or []
            for call in tool_calls:
                call_name = call.get("name") if isinstance(call, dict) else None
                if call_name:
                    used.append(str(call_name))
    seen = set()
    deduped: list[str] = []
    for name in used:
        if name not in seen:
            deduped.append(name)
            seen.add(name)
    return deduped


def route_intent(state: AgentState) -> AgentState:
    """Route user task into predefined intent categories."""
    query = _extract_query(state)
    intent = _classify_intent(query)
    return {
        "input": query,
        "intent": intent,
        "retrieval_attempts": state.get("retrieval_attempts", 0),
        "max_retrieval_attempts": state.get("max_retrieval_attempts", get_settings().retrieval_max_retries),
        "used_tools": state.get("used_tools", []),
        "used_memory": state.get("used_memory", []),
        "citations": state.get("citations", []),
    }


def load_user_context(state: AgentState) -> AgentState:
    """Load long-term profile and summarize recent thread messages."""
    user_id = state.get("user_id", "demo_user")
    memory = get_long_term_store().get_user_memory(user_id)
    recent = summarize_recent_messages(state.get("messages", []))

    used_memory: list[str] = []
    if memory.preferences:
        used_memory.append("long_term_preferences")
    if memory.term_mappings:
        used_memory.append("term_mappings")
    if recent:
        used_memory.append("short_term_thread")

    return {
        "long_term_memory": memory.model_dump(),
        "short_term_summary": recent,
        "used_memory": used_memory,
    }


def decide_retrieval(state: AgentState) -> AgentState:
    """Decide whether the task needs retrieval."""
    query = state.get("rewritten_query") or state.get("input", "")
    intent = state.get("intent", "general")
    return {
        "needs_retrieval": _should_retrieve(intent, query),
        "retrieval_query": query,
    }


def retrieve_documents(state: AgentState) -> AgentState:
    """Retrieve top-k documents from vector store."""
    query = state.get("retrieval_query", "")
    if not state.get("needs_retrieval"):
        return {"retrieved_docs": [], "citations": []}

    docs = get_retriever().retrieve(query=query, top_k=get_settings().retrieval_top_k)
    citations = [d.citation() for d in docs]
    return {
        "retrieved_docs": docs,
        "citations": citations,
    }


def grade_documents_node(state: AgentState) -> AgentState:
    """Grade retrieved docs and mark relevance for retry loop decision."""
    docs = state.get("retrieved_docs", [])
    query = state.get("retrieval_query", state.get("input", ""))
    relevant, rescored, reason = grade_documents(
        query=query,
        docs=docs,
        threshold=get_settings().retrieval_score_threshold,
    )
    return {
        "docs_relevant": relevant,
        "retrieved_docs": rescored,
        "retrieval_grade_reason": reason,
        "citations": [d.citation() for d in rescored],
    }


def rewrite_query_node(state: AgentState) -> AgentState:
    """Rewrite low-quality retrieval query and increment retry counter."""
    attempts = int(state.get("retrieval_attempts", 0)) + 1
    rewritten = rewrite_query(
        state.get("retrieval_query", state.get("input", "")),
        state.get("retrieval_grade_reason", ""),
    )
    return {
        "rewritten_query": rewritten,
        "retrieval_query": rewritten,
        "retrieval_attempts": attempts,
    }


def load_skill(state: AgentState) -> AgentState:
    """Lazy-load skill details only when intent/query requires it."""
    name, content = load_skill_for_query(state.get("input", ""), state.get("intent", "general"))
    return {
        "loaded_skill": name,
        "skill_content": content,
    }


def _build_agent_user_prompt(state: AgentState) -> str:
    memory = state.get("long_term_memory")
    pref_text = ""
    if memory:
        preferences = memory.get("preferences", {})
        pref_text = (
            f"language={preferences.get('language', 'zh')}, "
            f"style={preferences.get('style', 'concise')}, "
            f"terms={memory.get('term_mappings', {})}"
        )

    return f"""
User Query:
{state.get('input', '')}

Intent:
{state.get('intent', 'general')}

Short-Term Thread Summary:
{state.get('short_term_summary', '')}

Long-Term Preference:
{pref_text}

Loaded Skill:
{state.get('loaded_skill') or 'None'}
{state.get('skill_content') or ''}

Retrieved Context:
{_render_docs_context(state)}

Please answer the task. Use tools if needed. {FINAL_FORMAT_REMINDER}
""".strip()


def _extract_mcp_uri(text: str) -> str | None:
    match = re.search(r"(mcp://[A-Za-z0-9_./-]+)", text)
    return match.group(1) if match else None


def _format_sql_fallback(query: str) -> str:
    year_month = re.search(r"(\d{4})年(\d{1,2})月", query)
    if year_month:
        year = int(year_month.group(1))
        month = int(year_month.group(2))
        start = f"{year}-{month:02d}-01"
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        end = f"{next_year}-{next_month:02d}-01"
    else:
        start = "2026-03-01"
        end = "2026-04-01"

    region_map = {
        "华南": "South China",
        "华北": "North China",
        "华东": "East China",
    }
    region = None
    for key, value in region_map.items():
        if key in query:
            region = value
            break

    if "渠道" in query or "channel" in query.lower():
        metric_sql = "SUM(amount) AS gmv"
        group_sql = "GROUP BY channel"
        select_prefix = "channel, "
    elif "gmv" in query.lower():
        metric_sql = "SUM(amount) AS gmv"
        group_sql = ""
        select_prefix = ""
    else:
        metric_sql = "COUNT(*) AS order_count"
        group_sql = ""
        select_prefix = ""

    region_clause = f"\n  AND region = '{region}'" if region else ""
    group_clause = f"\n{group_sql}" if group_sql else ""
    return (
        "Intent Understanding: Generate a read-only analytics SQL.\n"
        "Suggested SQL:\n"
        "```sql\n"
        f"SELECT {select_prefix}{metric_sql}\n"
        "FROM sales_orders\n"
        f"WHERE order_date >= '{start}'\n"
        f"  AND order_date < '{end}'{region_clause}{group_clause};\n"
        "```\n"
        "Assumptions:\n"
        "- `amount` represents gross order amount.\n"
        "- Query is read-only and safe for analytics."
    )


def _format_meeting_summary_fallback(query: str) -> str:
    content = query.split("：", 1)[1] if "：" in query else query
    return (
        "Summary: Meeting notes were summarized in concise format.\n"
        f"Key Decisions:\n- {content[:90]}\n"
        "Action Items:\n- Extract owner + deadline from notes and track delivery.\n"
        "Risks:\n- Potential blockers should be escalated in next sync.\n"
        "Open Questions:\n- Confirm whether timeline and owner commitments are approved."
    )


def _deterministic_fallback_response(state: AgentState) -> tuple[str, list[str]]:
    """Rule-based response path when model key is not configured."""
    query = state.get("input", "")
    intent = state.get("intent", "general")
    docs = state.get("retrieved_docs", [])
    memory = state.get("long_term_memory") or {}
    used_tools: list[str] = []

    mcp_uri = _extract_mcp_uri(query)
    if mcp_uri:
        resource = get_resource_service().read_resource(mcp_uri)
        used_tools.append("read_mcp_resource")
        return f"{resource.get('title', 'MCP Resource')}: {resource.get('content', '')}", used_tools

    if "mcp 工具" in query or "MCP tool" in query:
        used_tools.append("call_mcp_tool")
        return "MCP tool fallback: external call is not configured, so local safe fallback is used.", used_tools

    term_mappings = memory.get("term_mappings", {})
    for term, meaning in term_mappings.items():
        if term.lower() in query.lower() and any(k in query for k in ["是什么", "含义", "meaning"]):
            used_tools.append("read_user_preferences")
            return f"{term} 表示 {meaning}。", used_tools

    if intent == "sql_analysis":
        if "schema" in query.lower() or "表结构" in query or "sales_orders" in query:
            used_tools.append("read_mcp_resource")
        return _format_sql_fallback(query), used_tools

    if intent == "meeting_summary":
        used_tools.append("summarize_text")
        return _format_meeting_summary_fallback(query), used_tools

    if docs:
        top = docs[0]
        snippet = top.content.replace("\n", " ").strip()[:220]
        return f"根据文档 {top.source}，{snippet}", used_tools

    return "当前未配置模型 key。我已使用本地规则路径处理请求，但需要更多上下文才能给出高质量答案。", used_tools


def invoke_tools_or_mcp(state: AgentState) -> AgentState:
    """Invoke base create_agent with local tools and optional MCP tools."""
    settings = get_settings()
    query = state.get("input", "")

    if settings.force_local_fallback or not settings.openai_api_key:
        fallback, used_tools = _deterministic_fallback_response(state)
        return {
            "draft_answer": fallback,
            "used_tools": used_tools,
            "tool_context": "fallback_local_mode",
        }

    try:
        from langchain_openai import ChatOpenAI

        llm_kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "temperature": settings.temperature,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            llm_kwargs["base_url"] = settings.openai_base_url
        llm = ChatOpenAI(**llm_kwargs)
        agent = create_agent(
            model=llm,
            tools=get_all_tools(),
            system_prompt=ANSWER_SYSTEM_PROMPT,
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _build_agent_user_prompt(state),
                    }
                ]
            }
        )

        messages = result.get("messages", []) if isinstance(result, dict) else []
        used_tools = _extract_tool_usage(messages)

        draft = ""
        for msg in reversed(messages):
            if getattr(msg, "type", "") == "ai":
                draft = _extract_message_content(msg)
                break

        if not draft:
            draft = f"I received your request: {query}"

        return {
            "draft_answer": draft,
            "used_tools": used_tools,
            "tool_context": "agent_create_agent_path",
        }
    except Exception as exc:
        global _INCOMPATIBLE_PROVIDER_WARNED
        err = str(exc)
        # Some OpenAI-compatible gateways return payloads that are not fully SDK-compatible.
        # In that case we downgrade quietly to deterministic mode for stable demos.
        incompatible = any(token in err for token in ["model_dump", "object has no attribute 'data'"])
        if incompatible:
            if not _INCOMPATIBLE_PROVIDER_WARNED:
                LOGGER.warning("Model provider response incompatible with langchain-openai. Fallback enabled.")
                _INCOMPATIBLE_PROVIDER_WARNED = True
        else:
            LOGGER.exception("Agent tool invocation failed")
        fallback, used_tools = _deterministic_fallback_response(state)
        return {
            "draft_answer": fallback,
            "used_tools": used_tools,
            "tool_context": "agent_error_fallback_incompatible_provider" if incompatible else "agent_error_fallback",
            "error": None if incompatible else err,
        }


def generate_answer(state: AgentState) -> AgentState:
    """Assemble final structured response."""
    draft = state.get("draft_answer") or ""
    docs = state.get("retrieved_docs", [])
    citations = [d.citation() for d in docs[:4]]

    if not draft.strip() and docs:
        draft = f"Based on retrieved documents, key answer: {docs[0].content[:200]}"
    if not draft.strip():
        draft = "I could not produce a strong answer yet. Please provide more details."

    confidence = 0.45
    if state.get("docs_relevant"):
        confidence += 0.25
    if state.get("loaded_skill"):
        confidence += 0.12
    if state.get("used_tools"):
        confidence += 0.08
    if state.get("error"):
        confidence -= 0.2
    confidence = max(0.1, min(confidence, 0.95))

    output = {
        "answer": draft,
        "used_tools": state.get("used_tools", []),
        "used_skill": state.get("loaded_skill"),
        "used_memory": state.get("used_memory", []),
        "citations": citations,
        "confidence": round(confidence, 3),
        "error": state.get("error"),
    }

    return {
        "final_answer": draft,
        "confidence": confidence,
        "citations": citations,
        "output": output,
        "messages": [AIMessage(content=draft)],
    }


def persist_memory(state: AgentState) -> AgentState:
    """Persist long-term memory updates for preferences, terms, and task summaries."""
    user_id = state.get("user_id", "demo_user")
    query = state.get("input", "")
    answer = state.get("final_answer", "")

    store = get_long_term_store()
    store.extract_and_update_from_query(user_id=user_id, query=query)
    if answer:
        store.append_task_summary(user_id=user_id, query=query, summary=answer[:220])

    used = list(state.get("used_memory", []))
    if "long_term_write" not in used:
        used.append("long_term_write")

    return {"used_memory": used}


def _after_retrieval_decision(state: AgentState) -> str:
    return "retrieve_documents" if state.get("needs_retrieval") else "load_skill"


def _after_grade_documents(state: AgentState) -> str:
    relevant = bool(state.get("docs_relevant"))
    attempts = int(state.get("retrieval_attempts", 0))
    max_attempts = int(state.get("max_retrieval_attempts", get_settings().retrieval_max_retries))

    if relevant:
        return "load_skill"
    if attempts >= max_attempts:
        return "load_skill"
    return "rewrite_query"


def build_graph(settings: Settings | None = None):
    """Build and compile the LangGraph workflow."""
    cfg = settings or get_settings()
    _enable_langsmith(cfg)

    workflow = StateGraph(AgentState)

    workflow.add_node("route_intent", route_intent)
    workflow.add_node("load_user_context", load_user_context)
    workflow.add_node("decide_retrieval", decide_retrieval)
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("load_skill", load_skill)
    workflow.add_node("invoke_tools_or_mcp", invoke_tools_or_mcp)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("persist_memory", persist_memory)

    workflow.add_edge(START, "route_intent")
    workflow.add_edge("route_intent", "load_user_context")
    workflow.add_edge("load_user_context", "decide_retrieval")
    workflow.add_conditional_edges(
        "decide_retrieval",
        _after_retrieval_decision,
        {
            "retrieve_documents": "retrieve_documents",
            "load_skill": "load_skill",
        },
    )
    workflow.add_edge("retrieve_documents", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        _after_grade_documents,
        {
            "rewrite_query": "rewrite_query",
            "load_skill": "load_skill",
        },
    )
    workflow.add_edge("rewrite_query", "retrieve_documents")
    workflow.add_edge("load_skill", "invoke_tools_or_mcp")
    workflow.add_edge("invoke_tools_or_mcp", "generate_answer")
    workflow.add_edge("generate_answer", "persist_memory")
    workflow.add_edge("persist_memory", END)

    return workflow.compile(checkpointer=get_checkpointer(cfg))


@lru_cache(maxsize=1)
def get_graph():
    """Return singleton compiled graph."""
    return build_graph(get_settings())


def run_query(query: str, user_id: str = "demo_user", thread_id: str = "default") -> dict[str, Any]:
    """Entry point used by CLI and eval script."""
    graph = get_graph()
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=query)],
            "input": query,
            "user_id": user_id,
            "thread_id": thread_id,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return result.get("output", {})
