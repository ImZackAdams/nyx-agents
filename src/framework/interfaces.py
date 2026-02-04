from typing import Protocol, Optional


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class ImageGenerator(Protocol):
    def generate_image(self, prompt: str) -> Optional[str]:
        ...


class NewsProvider(Protocol):
    def get_latest_article(self):
        ...

    def get_article_content(self, url: str) -> Optional[str]:
        ...


class Scheduler(Protocol):
    def next_action(self) -> str:
        ...


class ReplyHandler(Protocol):
    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        ...
