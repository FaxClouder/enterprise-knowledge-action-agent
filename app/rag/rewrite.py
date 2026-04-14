from __future__ import annotations

import re

from app.config import Settings, get_settings


def rewrite_query(query: str, failure_reason: str = "") -> str:
    """Rewrite query for a second retrieval pass with deterministic heuristics."""
    cleaned = re.sub(r"\s+", " ", query).strip()
    if not cleaned:
        return query

    replacements = {
        "报销": "差旅 报销 policy reimbursement",
        "请假": "leave vacation policy approval",
        "GMV": "gross merchandise volume sales metric",
        "会议纪要": "meeting notes action items decisions",
        "权限": "access control security policy",
    }

    expanded = cleaned
    for k, v in replacements.items():
        if k.lower() in cleaned.lower():
            expanded = f"{cleaned} {v}"

    if failure_reason:
        expanded = f"{expanded} focus_on:{failure_reason}"

    return expanded
