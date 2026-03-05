from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class VectorRecord:
    record_id: str
    vector: Dict[str, float]
    text: str
    metadata: Optional[dict] = None


class VectorStore:
    """In-memory vector store using sparse cosine similarity."""

    def __init__(self) -> None:
        self._records: List[VectorRecord] = []

    def add(self, record: VectorRecord) -> None:
        self._records.append(record)

    def add_many(self, records: Iterable[VectorRecord]) -> None:
        self._records.extend(records)

    def search(self, query_vec: Dict[str, float], top_k: int = 5) -> List[Tuple[VectorRecord, float]]:
        scored = []
        for record in self._records:
            score = _cosine_similarity(query_vec, record.vector)
            scored.append((record, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    for key, val in a.items():
        dot += val * b.get(key, 0.0)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
