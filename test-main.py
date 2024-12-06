import os
import time
import random
import logging
import warnings
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.prompts import get_all_prompts, FALLBACK_TWEETS
from bot.services.tweet_generator import TweetGenerator
from bot.services.reply_handler import ReplyHandler
from bot.services.meme_handler import MemeHandler
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass

# Suppress warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")

@dataclass
class SimulatedTweet:
    id: str
    text: str
    created_at: datetime
    author_username: str = "test_user"

    @staticmethod
    def generate_id() -> str:
        return str(random.randint(1000000000000000000, 9999999999999999999))

class SimulatedClient:
    def __init__(self):
        self.tweets: Dict[str, SimulatedTweet] = {}
        self.replies: Dict[str, List[SimulatedTweet]] = {}

    def create_tweet(self, text: str, in_reply_to_tweet_id: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        tweet_id = SimulatedTweet.generate_id()
        tweet = SimulatedTweet(
            id=tweet_id,
            text=text,
            created_at=datetime.now(),
            author_username="athena_bot" if not in_reply_to_tweet_id else "test_user"
        )
        self.tweets[tweet_id] = tweet
        if in_reply_to_tweet_id:
            if in_reply_to_tweet_id not in self.replies:
                self.replies[in_reply_to_tweet_id] = []
            self.replies[in_reply_to_tweet_id].append(tweet)
        print(f"[NEW TWEET] {tweet.text} (ID: {tweet_id})")
        return {"data": {"id": tweet_id}}

    def get_replies(self, tweet_id: str) -> List[SimulatedTweet]:
        return self.replies.get(tweet_id, [])

class ConsoleBot:
    """Simulated Console Bot for testing."""
    def __init__(self):
        self.logger = setup_logger("console_athena")
        self.logger.info("Starting simulated bot...")
        self._initialize_components()

    def _initialize_components(self):
        self.client = SimulatedClient()
        personality_bot = PersonalityBot(model_path="athena_8bit_model", logger=self.logger)
        self.tweet_generator = TweetGenerator(personality_bot, self.logger)
        self.reply_handler = ReplyHandler(self.client, self.tweet_generator, self.logger)
        self.meme_handler = MemeHandler(self.client, None, self.logger)

    def post_tweet(self) -> Optional[str]:
        """Simulate posting a tweet."""
        try:
            if self.meme_handler.should_post_meme():
                meme_id = self.meme_handler.post_meme()
                return meme_id

            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]

            for attempt in range(3):  # Simulated MAX_PROMPT_ATTEMPTS
                if not all_prompts:
                    break
                prompt = random.choice(all_prompts)
                all_prompts.remove(prompt)
                tweet = self.tweet_generator.generate_tweet(prompt)
                if tweet:
                    result = self.client.create_tweet(tweet)
                    return result["data"]["id"]

            fallback_tweet = random.choice(FALLBACK_TWEETS)
            result = self.client.create_tweet(fallback_tweet)
            return result["data"]["id"]

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}")
            return None

    def process_replies(self, tweet_id: str):
        """Allow user input to test replies."""
        print("\nEnter your replies (type 'exit' to stop replying):")
        while True:
            user_reply = input("\nYour reply: ")
            if user_reply.lower() == 'exit':
                print("Stopped accepting replies.")
                break
            self.logger.info(f"User replied: {user_reply}")
            # Create user reply in the simulated client
            user_reply_result = self.client.create_tweet(user_reply, in_reply_to_tweet_id=tweet_id)
            reply_id = user_reply_result["data"]["id"]
            # Generate bot response
            bot_response = self.tweet_generator.generate_tweet(user_reply)
            self.client.create_tweet(bot_response, in_reply_to_tweet_id=reply_id)
            print(f"[BOT RESPONSE] {bot_response}")

    def run(self):
        """Simulate bot operation."""
        print("\n=== Starting Simulated Bot ===")
        while True:
            tweet_id = self.post_tweet()
            if tweet_id:
                self.logger.info(f"Posted simulated tweet with ID: {tweet_id}")
                self.process_replies(tweet_id)
                time.sleep(5)  # Simulate POST_COOLDOWN
            else:
                self.logger.error("Failed to post tweet. Retrying...")
                time.sleep(2)

def main():
    load_dotenv()
    bot = ConsoleBot()
    bot.run()

if __name__ == "__main__":
    main()
