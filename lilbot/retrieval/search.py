from __future__ import annotations

from typing import List

from lilbot.memory.vector_store import VectorStore
from .embedder import SimpleEmbedder


def search(store: VectorStore, embedder: SimpleEmbedder, query: str, top_k: int = 5) -> List[dict]:
    query_vec = embedder.embed(query)
    results = store.search(query_vec, top_k=top_k)
    formatted = []
    for record, score in results:
        formatted.append(
            {
                "id": record.record_id,
                "score": score,
                "text": record.text,
                "source": (record.metadata or {}).get("source"),
            }
        )
    return formatted
