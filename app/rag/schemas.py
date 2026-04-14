from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedDocument:
    """Normalized retrieved document object used across graph nodes."""

    source: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def citation(self) -> str:
        """Return citation label for answer rendering."""
        return self.source
