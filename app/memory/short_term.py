from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings, get_settings


def _build_sqlite_checkpointer(path: Path):
    """Best-effort sqlite checkpointer; falls back when dependency is unavailable."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore

        conn = sqlite3.connect(str(path), check_same_thread=False)
        return SqliteSaver(conn)
    except Exception:
        return MemorySaver()


def get_checkpointer(settings: Settings | None = None):
    """Return short-term memory checkpointer for thread-scoped persistence."""
    cfg = settings or get_settings()
    checkpoint_path = cfg.memory_store_dir / "short_term_checkpoints.sqlite"
    return _build_sqlite_checkpointer(checkpoint_path)


def summarize_recent_messages(messages: list[BaseMessage], max_turns: int = 4) -> str:
    """Build compact short-term summary from recent messages."""
    if not messages:
        return ""
    clipped = messages[-max_turns * 2 :]
    lines: list[str] = []
    for msg in clipped:
        role = getattr(msg, "type", "message")
        content = str(getattr(msg, "content", ""))
        if content:
            lines.append(f"{role}: {content[:180]}")
    return "\n".join(lines)


def build_thread_config(thread_id: str) -> dict[str, Any]:
    """LangGraph configurable payload for thread-level continuation."""
    return {"configurable": {"thread_id": thread_id}}
