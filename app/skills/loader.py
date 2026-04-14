from __future__ import annotations

from functools import lru_cache

from app.skills.registry import SkillMeta, select_skill


@lru_cache(maxsize=8)
def _read_skill_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_skill_content(skill: SkillMeta) -> str:
    """Load full skill instruction only when selected."""
    return _read_skill_file(str(skill.path))


def load_skill_for_query(query: str, intent: str) -> tuple[str | None, str | None]:
    """Select and lazy-load skill content for the current task."""
    skill = select_skill(query=query, intent=intent)
    if not skill:
        return None, None
    return skill.name, load_skill_content(skill)
