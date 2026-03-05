from __future__ import annotations

import argparse

from lilbot.agent.runner import AgentRunner
from lilbot.llm.provider import EchoProvider
from lilbot.memory.vector_store import VectorStore
from lilbot.retrieval.embedder import SimpleEmbedder
from lilbot.retrieval.index import DocumentIndex
from lilbot.tools.docs_search import DocsSearchTool
from lilbot.tools.registry import ToolRegistry


def confirm_tool(name: str) -> bool:
    reply = input(f"Allow tool '{name}' to run? [y/N]: ")
    return reply.strip().lower() in {"y", "yes"}


def build_registry(doc_path: str | None) -> ToolRegistry:
    registry = ToolRegistry(allowlist={"search_docs"})

    store = VectorStore()
    embedder = SimpleEmbedder()
    index = DocumentIndex(embedder=embedder, store=store)

    if doc_path:
        index.load_from_folder(doc_path)

    registry.register(DocsSearchTool(store=store, embedder=embedder))
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(prog="lilbot")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run the agent")
    run_cmd.add_argument("--docs", help="Folder of docs to index", default=None)

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return

    llm = EchoProvider()
    registry = build_registry(args.docs)
    runner = AgentRunner(llm=llm, tools=registry, confirm=confirm_tool)

    user_request = input("Request: ")
    result = runner.run(user_request)
    print(f"\nResult (steps={result.steps}):\n{result.final}")


if __name__ == "__main__":
    main()
