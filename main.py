import os
import time
import random
import logging
import tweepy
import warnings
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet, post_image_with_tweet
from bot.text_cleaner import TextCleaner
from bot.rate_limiter import RateLimitTracker
from bot.prompts import get_all_prompts, MEME_CAPTIONS, FALLBACK_TWEETS

# Configuration Constants
MAX_TWEET_LENGTH = 220
MIN_TWEET_LENGTH = 180
MAX_GENERATION_ATTEMPTS = 3
REPLY_DELAY_SECONDS = 2
MEME_POSTING_CHANCE = 0.2

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

# Load environment variables
load_dotenv()

class TwitterBot:
    """Main Twitter bot implementation."""
    
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Starting the bot...")
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize all required components and connections."""
        self._validate_env_variables()
        self.bot = PersonalityBot(model_path="athena_8bit_model", logger=self.logger)
        self.client = setup_twitter_client()
        self.api = self._setup_tweepy_api()
        self.rate_limit_tracker = RateLimitTracker()
        self.tweet_cleaner = TextCleaner()

    def _validate_env_variables(self) -> None:
        """Ensure all required environment variables are set."""
        required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _setup_tweepy_api(self) -> tweepy.API:
        """Set up and return Tweepy API instance."""
        return tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))

    def _extract_tweet_content(self, text: str) -> str:
        """Extract the actual tweet content from the generated text."""
        # Split by "Tweet:" if present
        if "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            # Take only the first line
            text = text.split('\n')[0].strip()
        
        # Remove any generated usernames
        text = text.strip('"').strip()
        text = text.split("-Athena")[0].strip() if "-Athena" in text else text
        text = text.split("#CryptoTeaWithAthena")[0].strip()
        
        return text.strip()

    def _generate_tweet_response(self, prompt: str, max_attempts: int = 3) -> str:
        """Generate a tweet response with retry logic."""
        for attempt in range(max_attempts):
            try:
                response = self.bot.generate_response(prompt)
                if not response:
                    continue
                    
                cleaned_response = self.tweet_cleaner.clean_text(response)
                extracted_tweet = self._extract_tweet_content(cleaned_response)
                
                if (MIN_TWEET_LENGTH <= len(extracted_tweet) <= MAX_TWEET_LENGTH and
                    any(char.isalpha() for char in extracted_tweet)):
                    self.logger.info(f"Successfully generated tweet: {extracted_tweet}")
                    return extracted_tweet
                    
                self.logger.warning(
                    f"Generated response failed validation - Length: {len(extracted_tweet)}"
                )
                
            except Exception as e:
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
        
        return self._get_fallback_tweet()

    def _get_fallback_tweet(self) -> str:
        """Return a fallback tweet when generation fails."""
        tweet = random.choice(FALLBACK_TWEETS)
        self.logger.info(f"Using fallback tweet: {tweet}")
        return tweet

    def _handle_meme_post(self) -> Optional[str]:
        """Handle posting a meme with caption."""
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
        
        return post_image_with_tweet(self.client, self.api, caption, image_path, self.logger)

    def post_tweet(self) -> Optional[str]:
        """Post a new tweet, either text or meme."""
        self.logger.info("Starting tweet posting process...")
        
        try:
            # Handle meme posting chance
            if random.random() < MEME_POSTING_CHANCE:
                return self._handle_meme_post()

            # Handle text tweet
            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]
            
            # Try up to 3 different prompts before falling back
            for i in range(3):
                if not all_prompts:  # If we've used all prompts
                    break
                    
                prompt = random.choice(all_prompts)
                all_prompts.remove(prompt)  # Don't reuse the same prompt
                
                self.logger.info(f"Trying prompt {i + 1}/3: {prompt}")
                tweet = self._generate_tweet_response(prompt)
                
                if tweet and len(tweet) >= MIN_TWEET_LENGTH:
                    result = self.client.create_tweet(text=tweet)
                    return result.data.get('id')
                    
                self.logger.warning("Tweet generation failed, trying another prompt...")
            
            # If all prompts fail, use fallback
            tweet = self._get_fallback_tweet()
            result = self.client.create_tweet(text=tweet)
            return result.data.get('id')

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
            return None

    def reply_to_last_three(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Reply to the last three comments on a specific tweet."""
        try:
            bot_user_id = os.getenv("BOT_USER_ID")
            replies = search_replies_to_tweet(self.client, tweet_id, bot_user_id)
            
            if not replies:
                self.logger.info("No new replies found.")
                return since_id

            sorted_replies = sorted(replies, key=lambda x: x.id)
            new_replies = [reply for reply in sorted_replies if not since_id or reply.id > since_id]
            latest_replies = new_replies[-4:] if new_replies else []
            
            if not latest_replies:
                self.logger.info("No new replies since last check.")
                return since_id

            for reply in latest_replies:
                try:
                    self.logger.info(f"Processing reply: {reply.text}")
                    response = self._generate_tweet_response(reply.text)
                    
                    if not response:
                        response = f"@{reply.author.username} Thanks for engaging! 🤔"
                    
                    self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
                    time.sleep(REPLY_DELAY_SECONDS)
                    
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {str(e)}")
                    continue

            return max(reply.id for reply in latest_replies) if latest_replies else since_id

        except Exception as e:
            self.logger.error(f"Error in reply process: {str(e)}", exc_info=True)
            return since_id

    def run(self):
        """Main bot running loop."""
        since_id = None
        reply_check_interval = 60 * 15  # 15 minutes
        reply_cycles = 3
        post_cooldown = 60 * 60  # 45 minutes
        initial_wait = 60 * 10  # 10 minutes

        while True:
            try:
                self.logger.info("Starting new bot cycle...")
                
                # Do one final check for replies from previous tweet if we have a tweet_id
                if hasattr(self, 'last_tweet_id') and self.last_tweet_id:
                    self.logger.info("Checking for final replies on previous tweet...")
                    since_id = self.reply_to_last_three(self.last_tweet_id, since_id)
                
                tweet_id = self.post_tweet()
                if tweet_id:
                    self.logger.info(f"Posted tweet: {tweet_id}")
                    self.last_tweet_id = tweet_id  # Store for next cycle's final check

                    self.logger.info(f"Waiting {initial_wait // 60} minutes before starting reply cycles...")
                    time.sleep(initial_wait)
                    
                    for cycle in range(reply_cycles):
                        self.logger.info(f"Starting reply cycle {cycle + 1}/{reply_cycles}")
                        since_id = self.reply_to_last_three(tweet_id, since_id)
                        self.logger.info(f"Completed reply cycle {cycle + 1}")
                        
                        if cycle < reply_cycles - 1:
                            self.logger.info(f"Sleeping for {reply_check_interval // 60} minutes...")
                            time.sleep(reply_check_interval)

                    self.logger.info(f"Cooling down for {post_cooldown // 60} minutes...")
                    time.sleep(post_cooldown)
                else:
                    self.logger.error("Tweet posting failed. Retrying after cooldown...")
                    time.sleep(post_cooldown)
                    continue

            except tweepy.errors.TooManyRequests as e:
                self.rate_limit_tracker.add_rate_limit()
                reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
                sleep_time = self.rate_limit_tracker.get_sleep_time(reset_time)
                
                if self.rate_limit_tracker.should_extended_sleep():
                    self.logger.error(
                        f"Rate limit hit {self.rate_limit_tracker.threshold} times in "
                        f"{self.rate_limit_tracker.window_minutes} minutes. "
                        f"Sleeping for {self.rate_limit_tracker.backoff_hours} hours..."
                    )
                else:
                    self.logger.error("Rate limit hit. Retrying after cooldown...")
                
                self.logger.info(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            except Exception as e:
                self.logger.error("Error in main loop", exc_info=True)
                self.logger.info("Retrying after 15 minutes...")
                time.sleep(60 * 15)

def main():
    """Main entry point for the bot."""
    try:
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()