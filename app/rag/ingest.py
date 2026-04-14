from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings, get_settings

LOGGER = logging.getLogger(__name__)


def _load_single_file(path: Path):
    """Load a single document file using extension-specific loaders."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        from langchain_community.document_loaders import TextLoader

        return TextLoader(str(path), encoding="utf-8").load()
    if suffix == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        return PyPDFLoader(str(path)).load()
    return []


def load_documents(kb_dir: Path) -> list:
    """Load supported documents from knowledge base directory."""
    docs: list = []
    for path in kb_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"}:
            try:
                loaded = _load_single_file(path)
                for item in loaded:
                    item.metadata = dict(item.metadata or {})
                    item.metadata["source"] = path.name
                docs.extend(loaded)
            except Exception as exc:
                LOGGER.warning("Failed to load %s: %s", path, exc)
    return docs


def split_documents(documents: Iterable) -> list:
    """Split documents into chunks for vector indexing."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
    return splitter.split_documents(list(documents))


def ingest_knowledge_base(settings: Settings | None = None) -> dict[str, int | str]:
    """Build and persist Chroma vector store from knowledge base files."""
    cfg = settings or get_settings()
    docs = load_documents(cfg.kb_dir)
    if not docs:
        return {"documents": 0, "chunks": 0, "message": "No documents found."}

    chunks = split_documents(docs)
    if cfg.force_local_fallback or not cfg.openai_api_key:
        return {
            "documents": len(docs),
            "chunks": len(chunks),
            "message": "Vector indexing skipped (FORCE_LOCAL_FALLBACK=true or OPENAI_API_KEY missing). Lexical retrieval fallback is available.",
        }

    try:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        if cfg.vector_store_dir.exists():
            shutil.rmtree(cfg.vector_store_dir, ignore_errors=True)
        cfg.vector_store_dir.mkdir(parents=True, exist_ok=True)

        embedding_kwargs: dict[str, str] = {
            "model": cfg.openai_embedding_model,
            "api_key": cfg.openai_api_key or "",
        }
        if cfg.openai_base_url:
            embedding_kwargs["base_url"] = cfg.openai_base_url
        embeddings = OpenAIEmbeddings(**embedding_kwargs)
        vectorstore = Chroma(
            collection_name="enterprise_kb",
            embedding_function=embeddings,
            persist_directory=str(cfg.vector_store_dir),
        )
        vectorstore.add_documents(chunks)
        return {
            "documents": len(docs),
            "chunks": len(chunks),
            "message": f"Ingestion completed into {cfg.vector_store_dir}",
        }
    except Exception as exc:
        LOGGER.warning("Vector ingestion failed, degrade to lexical retrieval: %s", exc)
        return {
            "documents": len(docs),
            "chunks": len(chunks),
            "message": f"Vector ingestion failed ({exc}). Lexical retrieval fallback remains available.",
        }
