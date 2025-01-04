"""
Simplified simulation version of the Twitter bot for content testing.
"""
import time
import warnings
import logging
import os
from typing import List
from dotenv import load_dotenv

from utils.logger import setup_logger
from bot.initializers import (
    validate_env_variables,
    initialize_diffusion_pipeline,
    setup_twitter_api
)

from bot.posting.posting_service import PostingService
from bot.main_bot import PersonalityBot
from bot.posting.tweet_generator import TweetGenerator
from bot.posting.meme_poster import MemePoster
from bot.posting.reply_poster import ReplyPoster
from bot.news.news_service import NewsService

# Configure logging to only show errors
logging.getLogger().setLevel(logging.ERROR)
for handler in logging.getLogger().handlers:
    handler.setLevel(logging.ERROR)

def disable_loggers():
    """Disable all known loggers"""
    loggers = [
        'athena_sim',
        'accelerate.utils.modeling',
        'asyncio',
        'PIL',
        'boto3',
        'botocore',
        'urllib3',
        'tweepy',
        'tqdm',
        'diffusers'
    ]
    for logger_name in loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
        logging.getLogger(logger_name).propagate = False

class MockTwitterClient:
    def __init__(self):
        self.tweet_counter = 0
        self.tweets = {}

    def create_tweet(self, text=None, media_ids=None):
        self.tweet_counter += 1
        tweet_id = f'mock_tweet_{self.tweet_counter}'
        self.tweets[tweet_id] = {
            'text': text,
            'id': tweet_id,
            'created_at': time.time()
        }
        return type('MockResponse', (), {'data': self.tweets[tweet_id]})

class SimulatedTwitterBot:
    def __init__(self):
        disable_loggers()  # Disable all known loggers
        print("\n🤖 Initializing Bot Test...\n")
        self.logger = setup_logger("athena_sim")
        self.client = MockTwitterClient()
        self._initialize_components()

    def _initialize_components(self) -> None:
        try:
            validate_env_variables(self.logger)
            self.api = self.client
            
            src_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(src_dir, "ml", "text", "model_files", "falcon3_10b_instruct")
            
            personality_bot = PersonalityBot(model_path=model_path, logger=self.logger)
            tweet_generator = TweetGenerator(personality_bot, logger=self.logger)
            
            print("Loading models...")
            self.pipe = initialize_diffusion_pipeline(self.logger)
            
            news_service = NewsService(logger=self.logger)
            meme_handler = MemePoster(client=self.client, api=self.api, logger=self.logger)

            self.posting_service = PostingService(
                self.client,
                tweet_generator,
                news_service,
                meme_handler,
                self.logger
            )
            print("✅ Ready!\n")

        except Exception as e:
            print(f"\n❌ Initialization failed: {str(e)}")
            raise

    def run(self, num_iterations: int = 10) -> None:
        """Generate specified number of tweets with clean output format"""
        print(f"📝 Generating {num_iterations} test tweets...\n")
        
        successful_tweets = 0
        
        for i in range(num_iterations):
            try:
                print(f"Tweet {i + 1}/{num_iterations}")
                print("-" * 80)
                
                tweet_id = self.posting_service.post_tweet()
                
                if tweet_id:
                    tweet = self.client.tweets[tweet_id]
                    print(f"{tweet['text']}")
                    print(f"\nLength: {len(tweet['text'])} characters")
                    successful_tweets += 1
                
                print("-" * 80 + "\n")
                
                if i < num_iterations - 1:
                    time.sleep(3)

            except Exception as e:
                print(f"❌ Error generating tweet {i + 1}\n")
                continue

        print(f"✅ Test completed! Generated {successful_tweets} tweets successfully\n")

def main():
    try:
        warnings.filterwarnings("ignore")
        load_dotenv()
        bot = SimulatedTwitterBot()
        bot.run(num_iterations=10)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    main()