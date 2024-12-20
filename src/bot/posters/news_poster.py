from typing import Optional
import random
from bot.configs.posting_config import MAX_PROMPT_ATTEMPTS

class NewsPoster:
    def __init__(self, tweet_generator, news_service, client, logger):
        self.tweet_generator = tweet_generator
        self.news_service = news_service
        self.client = client
        self.logger = logger

    def post_news_tweet(self) -> Optional[str]:
        """Posts a news-related tweet."""
        try:
            self.logger.info("Fetching the latest crypto news...")
            article = self.news_service.get_latest_article()

            if not article:
                self.logger.info("No new articles found.")
                return None

            self.logger.info(f"Processing article: {article.title}")
            article.content = self.news_service.get_article_content(article.url)

            if not article.content:
                self.logger.warning("Failed to extract article content.")
                return None

            for attempt in range(MAX_PROMPT_ATTEMPTS):
                self.logger.info(f"Generating news tweet, attempt {attempt + 1}/{MAX_PROMPT_ATTEMPTS}...")
                prompt = self._generate_news_prompt(article)
                raw_tweet = self.tweet_generator.generate_tweet(prompt)

                if not raw_tweet:
                    continue

                # Post raw tweet directly since format_tweet and validate_tweet are removed
                tweet_id = self._post_to_twitter(raw_tweet)
                if tweet_id:
                    self.news_service.mark_as_posted(article)
                    self.logger.info(f"Successfully posted news tweet: {raw_tweet}")
                    return tweet_id

            self.logger.warning("Failed to generate a valid news tweet.")
            return None

        except Exception as e:
            self.logger.error(f"Error posting news tweet: {e}", exc_info=True)
            return None

    def _generate_news_prompt(self, article) -> str:
        """Generates a prompt for the news tweet."""
        return (
            f"You are Athena (@Athena_TBALL), queen of crypto Twitter.\n"
            f"Title: {article.title}\nContent: {article.content[:200]}\n\n"
            "Write a sassy tweet summarizing this news."
        )

    def _post_to_twitter(self, text: str) -> Optional[str]:
        """Posts a tweet to Twitter and returns the tweet ID."""
        try:
            response = self.client.create_tweet(text=text)
            return response.data.get('id')
        except Exception as e:
            self.logger.error(f"Failed to post tweet: {e}")
            return None
