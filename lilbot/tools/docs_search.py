from __future__ import annotations

from typing import Any, Dict

from lilbot.retrieval.search import search as search_docs
from lilbot.retrieval.embedder import SimpleEmbedder
from lilbot.memory.vector_store import VectorStore
from lilbot.tools.base_tool import Tool
from lilbot.tools.registry import get_registry


class DocsSearchTool(Tool):
    name = "search_docs"
    description = "Search indexed documents and return top matches"
    input_schema = {"query": "string", "top_k": "int"}

    def __init__(self, store: VectorStore, embedder: SimpleEmbedder | None = None) -> None:
        self.store = store
        self.embedder = embedder or SimpleEmbedder()

    def run(self, input_data: Dict[str, Any]) -> Any:
        query = input_data.get("query", "")
        top_k = int(input_data.get("top_k", 5))
        return search_docs(self.store, self.embedder, query, top_k=top_k)


def register_docs_search(store: VectorStore, embedder: SimpleEmbedder | None = None) -> DocsSearchTool:
    tool = DocsSearchTool(store=store, embedder=embedder)
    get_registry().register(tool)
    return tool
