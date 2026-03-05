from __future__ import annotations

import re
from collections import Counter
from typing import Dict


class SimpleEmbedder:
    """Lightweight bag-of-words embedder (no external deps)."""

    def embed(self, text: str) -> Dict[str, float]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        counts = Counter(tokens)
        total = float(sum(counts.values())) or 1.0
        return {token: count / total for token, count in counts.items()}
