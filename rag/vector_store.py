"""Persistent ChromaDB vector store with HuggingFace sentence-transformer embeddings."""
import os
from functools import lru_cache
from pathlib import Path

from .knowledge_base import all_documents

PERSIST_DIR = Path(__file__).resolve().parent.parent / "chroma_db"
COLLECTION = "coding_knowledge"


@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))


def _seed(store) -> int:
    """Insert only documents whose ids are not already stored (no duplicates across runs)."""
    docs = all_documents()
    existing = set(store.get(ids=[d["id"] for d in docs]).get("ids", []))
    new = [d for d in docs if d["id"] not in existing]
    if new:
        store.add_texts(
            texts=[d["text"] for d in new],
            metadatas=[{k: d[k] for k in ("language", "topic", "type", "source")} for d in new],
            ids=[d["id"] for d in new],
        )
    return len(new)


@lru_cache(maxsize=1)
def get_store():
    from langchain_chroma import Chroma
    PERSIST_DIR.mkdir(exist_ok=True)
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(PERSIST_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    _seed(store)
    return store


def list_documents():
    """Everything stored in ChromaDB (for the 'stored knowledge' demo)."""
    data = get_store().get()
    rows = []
    for i, doc_id in enumerate(data["ids"]):
        meta = data["metadatas"][i] or {}
        rows.append({"id": doc_id, **meta, "text": data["documents"][i]})
    return sorted(rows, key=lambda r: r["id"])
