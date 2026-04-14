from __future__ import annotations

import logging
import re
from functools import lru_cache

from app.config import Settings, get_settings
from app.rag.schemas import RetrievedDocument

LOGGER = logging.getLogger(__name__)


class KnowledgeBaseRetriever:
    """Thin retriever facade over Chroma vector store."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._vectorstore = None
        self._vector_failed = False

    def _get_vectorstore(self):
        if self._vector_failed:
            return None
        if self._vectorstore is not None:
            return self._vectorstore

        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        embedding_kwargs: dict[str, str] = {
            "model": self.settings.openai_embedding_model,
            "api_key": self.settings.openai_api_key or "",
        }
        if self.settings.openai_base_url:
            embedding_kwargs["base_url"] = self.settings.openai_base_url
        try:
            embeddings = OpenAIEmbeddings(**embedding_kwargs)
            self._vectorstore = Chroma(
                collection_name="enterprise_kb",
                embedding_function=embeddings,
                persist_directory=str(self.settings.vector_store_dir),
            )
            return self._vectorstore
        except Exception as exc:
            LOGGER.warning("Vectorstore init failed, switch to lexical fallback: %s", exc)
            self._vector_failed = True
            return None

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.split(r"[^\w]+", text.lower()) if token}

    def _lexical_fallback_retrieve(self, query: str, k: int) -> list[RetrievedDocument]:
        """Fallback retriever based on keyword overlap from local documents."""
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        docs: list[RetrievedDocument] = []
        for path in self.settings.kb_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="utf-8", errors="ignore")
            d_tokens = self._tokenize(content[:3000])
            if not d_tokens:
                continue
            overlap = len(q_tokens.intersection(d_tokens)) / max(len(q_tokens), 1)
            if overlap <= 0:
                continue
            docs.append(
                RetrievedDocument(
                    source=path.name,
                    content=content[:2500],
                    score=float(overlap),
                    metadata={"source": path.name, "retrieval_mode": "lexical_fallback"},
                )
            )

        docs.sort(key=lambda d: d.score, reverse=True)
        return docs[:k]

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedDocument]:
        """Retrieve top-k documents and normalize payload."""
        k = top_k or self.settings.retrieval_top_k
        if not query.strip():
            return []

        if self.settings.force_local_fallback or not self.settings.openai_api_key:
            return self._lexical_fallback_retrieve(query, k)

        try:
            vectorstore = self._get_vectorstore()
            if vectorstore is None:
                return self._lexical_fallback_retrieve(query, k)
            pairs = vectorstore.similarity_search_with_relevance_scores(query, k=k)
            results: list[RetrievedDocument] = []
            for doc, score in pairs:
                src = doc.metadata.get("source", "unknown")
                results.append(
                    RetrievedDocument(
                        source=str(src),
                        content=doc.page_content,
                        score=float(score),
                        metadata=doc.metadata,
                    )
                )
            return results
        except Exception as exc:
            LOGGER.warning("Retriever failed, using lexical fallback: %s", exc)
            self._vector_failed = True
            return self._lexical_fallback_retrieve(query, k)


@lru_cache(maxsize=1)
def get_retriever(settings: Settings | None = None) -> KnowledgeBaseRetriever:
    """Return singleton retriever."""
    cfg = settings or get_settings()
    return KnowledgeBaseRetriever(cfg)
