from __future__ import annotations

import json

from app.config import get_settings
from app.rag.ingest import ingest_knowledge_base


def main() -> None:
    """CLI script for knowledge base ingestion."""
    settings = get_settings()
    report = ingest_knowledge_base(settings)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
