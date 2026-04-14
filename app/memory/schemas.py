from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """Stable user preferences for cross-session personalization."""

    language: Literal["zh", "en", "bilingual"] = "zh"
    style: Literal["concise", "detailed", "bullet"] = "concise"


class TaskSummary(BaseModel):
    """Condensed historical task summary for memory replay."""

    query: str
    summary: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserLongTermMemory(BaseModel):
    """Structured long-term memory record."""

    user_id: str
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    term_mappings: dict[str, str] = Field(default_factory=dict)
    task_summaries: list[TaskSummary] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        """Update the timestamp after any mutation."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
