import os
import time
import random
import logging
import warnings
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.text_cleaner import TextCleaner
from bot.prompts import get_all_prompts, MEME_CAPTIONS, FALLBACK_TWEETS
from dataclasses import dataclass
from datetime import datetime

# Configuration Constants
MAX_TWEET_LENGTH = 220
MIN_TWEET_LENGTH = 100
MAX_GENERATION_ATTEMPTS = 3
REPLY_DELAY_SECONDS = 2
MEME_POSTING_CHANCE = 0.2

# Suppress warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

@dataclass
class SimulatedTweet:
    id: str
    text: str
    created_at: datetime
    author_username: str = "test_user"
    
    @classmethod
    def generate_id(cls) -> str:
        return str(random.randint(1000000000000000000, 9999999999999999999))

class SimulatedClient:
    def __init__(self):
        self.tweets: Dict[str, SimulatedTweet] = {}
        self.replies: Dict[str, List[SimulatedTweet]] = {}
        
    def create_tweet(self, text: str, in_reply_to_tweet_id: Optional[str] = None) -> Dict[str, Any]:
        tweet_id = SimulatedTweet.generate_id()
        tweet = SimulatedTweet(
            id=tweet_id,
            text=text,
            created_at=datetime.now(),
            author_username="athena_bot" if not in_reply_to_tweet_id else "user"
        )
        
        self.tweets[tweet_id] = tweet
        
        if in_reply_to_tweet_id:
            if in_reply_to_tweet_id not in self.replies:
                self.replies[in_reply_to_tweet_id] = []
            self.replies[in_reply_to_tweet_id].append(tweet)
            
        return {"data": {"id": tweet_id}}

    def get_tweet(self, tweet_id: str) -> Optional[SimulatedTweet]:
        return self.tweets.get(tweet_id)

    def get_replies(self, tweet_id: str) -> List[SimulatedTweet]:
        return self.replies.get(tweet_id, [])

class ConsoleBot:
    def __init__(self):
        self.logger = setup_logger("console_athena")
        self.logger.info("Starting the console bot...")
        self._initialize_components()
        self.fallback_tweets = FALLBACK_TWEETS
        
    def _initialize_components(self) -> None:
        self.bot = PersonalityBot(model_path="athena_8bit_model", logger=self.logger)
        self.client = SimulatedClient()
        self.tweet_cleaner = TextCleaner()

    def _extract_tweet_content(self, text: str) -> str:
        if "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            text = text.split('\n')[0].strip()
        
        text = text.strip('"').strip()
        text = text.split("-Athena")[0].strip() if "-Athena" in text else text
        text = text.split("#CryptoTeaWithAthena")[0].strip()
        
        return text.strip()

    def _get_fallback_tweet(self) -> str:
        tweet = random.choice(self.fallback_tweets)
        self.logger.info(f"Using fallback tweet: {tweet}")
        return tweet

    def _generate_tweet_response(self, prompt: str, max_attempts: int = 3) -> str:
        for attempt in range(max_attempts):
            try:
                response = self.bot.generate_response(prompt)
                if not response:
                    continue
                    
                cleaned_response = self.tweet_cleaner.clean_text(response)
                extracted_tweet = self._extract_tweet_content(cleaned_response)
                
                if (MIN_TWEET_LENGTH <= len(extracted_tweet) <= MAX_TWEET_LENGTH and
                    any(char.isalpha() for char in extracted_tweet)):
                    self.logger.info(f"Generated tweet: {extracted_tweet}")
                    return extracted_tweet
                    
                self.logger.warning(
                    f"Generated response failed validation - Length: {len(extracted_tweet)}"
                )
                
            except Exception as e:
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
        
        return self._get_fallback_tweet()

    def _handle_meme_post(self) -> Optional[str]:
        memes_folder = os.path.join(os.getcwd(), 'memes')
        if not os.path.exists(memes_folder):
            self.logger.error(f"Memes folder not found at {memes_folder}")
            return None

        supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
        images = [f for f in os.listdir(memes_folder) if f.lower().endswith(supported_formats)]
        
        if not images:
            return None

        image_path = os.path.join(memes_folder, random.choice(images))
        caption = random.choice(MEME_CAPTIONS)
        
        print(f"\n[MEME POST] Would post image: {image_path}")
        print(f"Caption: {caption}")
        
        result = self.client.create_tweet(text=caption)
        return result["data"]["id"]

    def post_tweet(self) -> Optional[str]:
        self.logger.info("Starting tweet posting process...")
        
        try:
            if random.random() < MEME_POSTING_CHANCE:
                return self._handle_meme_post()

            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]
            
            for i in range(3):
                if not all_prompts:
                    break
                    
                prompt = random.choice(all_prompts)
                all_prompts.remove(prompt)
                
                self.logger.info(f"Trying prompt {i + 1}/3: {prompt}")
                tweet = self._generate_tweet_response(prompt)
                
                if tweet and len(tweet) >= MIN_TWEET_LENGTH:
                    result = self.client.create_tweet(text=tweet)
                    print(f"\n[NEW TWEET] {tweet}")
                    return result["data"]["id"]
                    
                self.logger.warning("Tweet generation failed, trying another prompt...")
            
            tweet = self._get_fallback_tweet()
            result = self.client.create_tweet(text=tweet)
            print(f"\n[FALLBACK TWEET] {tweet}")
            return result["data"]["id"]

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}")
            return None

    def process_user_input(self, tweet_id: str) -> None:
        print("\nEnter your replies (press Ctrl+C to stop responding):")
        
        try:
            while True:
                user_reply = input("\nYour reply (or Ctrl+C to stop): ")
                
                # Create user reply
                reply_result = self.client.create_tweet(text=user_reply, in_reply_to_tweet_id=tweet_id)
                reply_id = reply_result["data"]["id"]
                
                # Generate and show bot's response
                response = self._generate_tweet_response(user_reply)
                self.client.create_tweet(text=response, in_reply_to_tweet_id=reply_id)
                print(f"\n[BOT RESPONSE] {response}")
                
        except KeyboardInterrupt:
            print("\nStopped accepting replies.")

    def run(self):
        print("\n=== Console Bot Started ===")
        print("This version will post tweets and let you interact with them.")
        print("Press Ctrl+C to stop the bot at any time.")
        print("===========================\n")

        try:
            while True:
                tweet_id = self.post_tweet()
                if tweet_id:
                    self.process_user_input(tweet_id)
                    
                    print("\nWaiting before next tweet...")
                    time.sleep(5)  # Short delay for testing
                else:
                    print("\nFailed to generate tweet. Retrying...")
                    time.sleep(2)

        except KeyboardInterrupt:
            print("\nBot stopped by user.")
        except Exception as e:
            self.logger.error("Error in main loop", exc_info=True)
            print("\nBot stopped due to error.")

def main():
    try:
        bot = ConsoleBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()