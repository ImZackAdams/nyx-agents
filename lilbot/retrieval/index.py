from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List

from lilbot.memory.vector_store import VectorRecord, VectorStore
from .embedder import SimpleEmbedder


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source: str


class DocumentIndex:
    def __init__(self, embedder: SimpleEmbedder | None = None, store: VectorStore | None = None):
        self.embedder = embedder or SimpleEmbedder()
        self.store = store or VectorStore()

    def index_documents(self, docs: Iterable[DocumentChunk]) -> None:
        records: List[VectorRecord] = []
        for doc in docs:
            vec = self.embedder.embed(doc.text)
            records.append(
                VectorRecord(
                    record_id=doc.chunk_id,
                    vector=vec,
                    text=doc.text,
                    metadata={"source": doc.source},
                )
            )
        self.store.add_many(records)

    def load_from_folder(self, folder: str, chunk_size: int = 500) -> None:
        docs: List[DocumentChunk] = []
        for root, _, files in os.walk(folder):
            for name in files:
                path = os.path.join(root, name)
                if not _is_text_file(path):
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for idx, chunk in enumerate(_chunk_text(content, chunk_size)):
                    chunk_id = f"{path}:{idx}"
                    docs.append(DocumentChunk(chunk_id=chunk_id, text=chunk, source=path))
        self.index_documents(docs)


def _chunk_text(text: str, chunk_size: int) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def _is_text_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in {".txt", ".md", ".py", ".rst", ".yaml", ".yml"}
