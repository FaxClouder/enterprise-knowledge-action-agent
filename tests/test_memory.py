from __future__ import annotations

from app.memory.long_term import get_long_term_store


def test_long_term_preferences_roundtrip() -> None:
    store = get_long_term_store()
    uid = "pytest_user_memory"
    store.update_preferences(uid, language="en", style="bullet")
    memory = store.get_user_memory(uid)
    assert memory.preferences.language == "en"
    assert memory.preferences.style == "bullet"


def test_term_mapping_update() -> None:
    store = get_long_term_store()
    uid = "pytest_user_terms"
    store.upsert_term_mapping(uid, "SLA", "service level agreement")
    memory = store.get_user_memory(uid)
    assert memory.term_mappings.get("SLA") == "service level agreement"
