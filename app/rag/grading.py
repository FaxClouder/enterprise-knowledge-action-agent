from __future__ import annotations

import math
import re

from app.rag.schemas import RetrievedDocument


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.split(r"[^\w]+", text.lower()) if tok}


def grade_documents(
    query: str,
    docs: list[RetrievedDocument],
    threshold: float = 0.18,
) -> tuple[bool, list[RetrievedDocument], str]:
    """Re-rank documents with lexical overlap and judge retrieval quality."""
    if not docs:
        return False, [], "No documents retrieved"

    q_tokens = _tokenize(query)
    if not q_tokens:
        return False, docs, "Query is empty"

    rescored: list[RetrievedDocument] = []
    for doc in docs:
        d_tokens = _tokenize(doc.content[:1200])
        overlap = len(q_tokens.intersection(d_tokens)) / max(len(q_tokens), 1)
        semantic = max(doc.score, 0.0)
        combined = 0.65 * semantic + 0.35 * overlap
        rescored.append(
            RetrievedDocument(
                source=doc.source,
                content=doc.content,
                score=combined,
                metadata=doc.metadata,
            )
        )

    rescored.sort(key=lambda x: x.score, reverse=True)
    avg_top = sum(d.score for d in rescored[:2]) / min(2, len(rescored))
    relevant = avg_top >= threshold
    reason = f"avg_top={avg_top:.3f}, threshold={threshold:.3f}"
    return relevant, rescored, reason
