from __future__ import annotations

import argparse

import os

from lilbot.agent.runner import AgentRunner
from lilbot.llm.provider import EchoProvider, LocalHFProvider
from lilbot.memory.vector_store import VectorStore
from lilbot.retrieval.embedder import SimpleEmbedder
from lilbot.retrieval.index import DocumentIndex
from lilbot.tools.docs_search import DocsSearchTool
from lilbot.tools.registry import ToolRegistry
from lilbot.tools.news_fetch import FetchLatestNewsTool
from lilbot.tools.twitter_post import PostTweetTool
from lilbot.integrations.news.news_service import NewsService
from lilbot.integrations.twitter.client import TwitterClient


def confirm_tool(name: str) -> bool:
    reply = input(f"Allow tool '{name}' to run? [y/N]: ")
    return reply.strip().lower() in {"y", "yes"}


def build_registry(doc_path: str | None) -> ToolRegistry:
    allowlist = {"search_docs"}
    registry = ToolRegistry(allowlist=allowlist)

    store = VectorStore()
    embedder = SimpleEmbedder()
    index = DocumentIndex(embedder=embedder, store=store)

    if doc_path:
        index.load_from_folder(doc_path)

    registry.register(DocsSearchTool(store=store, embedder=embedder))

    if os.getenv("NEWS_FEEDS"):
        news_service = NewsService()
        registry.register(FetchLatestNewsTool(news_service))
        allowlist.add("fetch_latest_news")

    try:
        twitter_client = TwitterClient()
        registry.register(PostTweetTool(twitter_client))
        allowlist.add("post_tweet")
    except Exception:
        pass
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(prog="lilbot")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run the agent")
    run_cmd.add_argument("--docs", help="Folder of docs to index", default=None)
    run_cmd.add_argument("--model-path", help="Local HF model path", default=None)
    run_cmd.add_argument("--device", help="auto|cpu|cuda", default="auto")
    run_cmd.add_argument("--max-new-tokens", type=int, default=200)
    run_cmd.add_argument("--quantize-4bit", action="store_true", help="Enable 4-bit quantization (GPU)")

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return

    if args.model_path:
        llm = LocalHFProvider(
            args.model_path,
            device=args.device,
            max_new_tokens=args.max_new_tokens,
            quantize_4bit=args.quantize_4bit,
        )
    else:
        llm = EchoProvider()
    registry = build_registry(args.docs)
    runner = AgentRunner(llm=llm, tools=registry, confirm=confirm_tool)

    while True:
        user_request = input("Request (or 'exit'): ").strip()
        if not user_request:
            continue
        if user_request.lower() in {"exit", "quit"}:
            print("Bye.")
            return

        result = runner.run(user_request)
        print(f"\nResult (steps={result.steps}):\n{result.final}\n")


if __name__ == "__main__":
    main()
