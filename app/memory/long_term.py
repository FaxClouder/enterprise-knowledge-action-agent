from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock

from app.config import Settings, get_settings
from app.memory.schemas import TaskSummary, UserLongTermMemory


class LongTermMemoryStore:
    """JSON-backed long-term memory store with structured records."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = Lock()
        self._bootstrap()

    def _bootstrap(self) -> None:
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _read_all(self) -> dict[str, dict]:
        with self._lock:
            return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _write_all(self, payload: dict[str, dict]) -> None:
        with self._lock:
            self.file_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def get_user_memory(self, user_id: str) -> UserLongTermMemory:
        """Load memory for one user, creating default record if missing."""
        all_data = self._read_all()
        record = all_data.get(user_id)
        if not record:
            memory = UserLongTermMemory(user_id=user_id)
            all_data[user_id] = memory.model_dump()
            self._write_all(all_data)
            return memory
        return UserLongTermMemory.model_validate(record)

    def save_user_memory(self, memory: UserLongTermMemory) -> None:
        """Persist one user memory object."""
        all_data = self._read_all()
        memory.touch()
        all_data[memory.user_id] = memory.model_dump()
        self._write_all(all_data)

    def update_preferences(self, user_id: str, *, language: str | None = None, style: str | None = None) -> UserLongTermMemory:
        """Update user output preferences."""
        memory = self.get_user_memory(user_id)
        if language in {"zh", "en", "bilingual"}:
            memory.preferences.language = language
        if style in {"concise", "detailed", "bullet"}:
            memory.preferences.style = style
        self.save_user_memory(memory)
        return memory

    def upsert_term_mapping(self, user_id: str, term: str, meaning: str) -> UserLongTermMemory:
        """Store or update organization term mapping."""
        memory = self.get_user_memory(user_id)
        memory.term_mappings[term.strip()] = meaning.strip()
        self.save_user_memory(memory)
        return memory

    def append_task_summary(self, user_id: str, query: str, summary: str, max_items: int = 20) -> UserLongTermMemory:
        """Append compact task summary and truncate history."""
        memory = self.get_user_memory(user_id)
        memory.task_summaries.append(TaskSummary(query=query[:300], summary=summary[:500]))
        if len(memory.task_summaries) > max_items:
            memory.task_summaries = memory.task_summaries[-max_items:]
        self.save_user_memory(memory)
        return memory

    def extract_and_update_from_query(self, user_id: str, query: str) -> UserLongTermMemory:
        """Heuristically extract preference and term signals from user text."""
        memory = self.get_user_memory(user_id)
        q = query.strip()

        if any(token in q.lower() for token in ["use english", "英文", "english only"]):
            memory.preferences.language = "en"
        if any(token in q for token in ["用中文", "中文回答"]):
            memory.preferences.language = "zh"
        if any(token in q.lower() for token in ["bilingual", "中英"]):
            memory.preferences.language = "bilingual"

        if any(token in q.lower() for token in ["简洁", "concise", "short answer"]):
            memory.preferences.style = "concise"
        if any(token in q.lower() for token in ["详细", "detailed", "expand"]):
            memory.preferences.style = "detailed"
        if any(token in q.lower() for token in ["bullet", "列表", "条目"]):
            memory.preferences.style = "bullet"

        term_match = re.search(r"术语\s*([A-Za-z0-9_-]+)\s*表示\s*(.+)$", q)
        if term_match:
            memory.term_mappings[term_match.group(1).strip()] = term_match.group(2).strip()

        self.save_user_memory(memory)
        return memory


_STORE: LongTermMemoryStore | None = None


def get_long_term_store(settings: Settings | None = None) -> LongTermMemoryStore:
    """Return singleton long-term memory store."""
    global _STORE
    if _STORE is None:
        cfg = settings or get_settings()
        _STORE = LongTermMemoryStore(cfg.memory_store_dir / "long_term_memory.json")
    return _STORE
