import os
import time
import random
import logging
import warnings
import tweepy
from typing import Optional
from dotenv import load_dotenv

from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.services.utils import setup_twitter_client
from bot.services.rate_limiter import RateLimitTracker
from bot.prompts import get_all_prompts, FALLBACK_TWEETS
from bot.services.tweet_generator import TweetGenerator
from bot.services.reply_handler import ReplyHandler
from bot.services.meme_handler import MemeHandler
from bot.services.news_service import NewsService
from bot.configs.posting_config import (
    POST_COOLDOWN,
    RETRY_DELAY,
    MAX_PROMPT_ATTEMPTS,
    NEWS_POSTING_CHANCE,
    MEME_POSTING_CHANCE
)

# Additional imports for Stable Diffusion
import torch
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline

class TwitterBot:
    """Main Twitter bot implementation."""
    
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Starting the bot...")
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize all required components and connections."""
        self._validate_env_variables()
        
        # Set up main components and API
        self.client = setup_twitter_client()
        self.api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))
        self.rate_limit_tracker = RateLimitTracker()
        
        # Initialize personality bot
        personality_bot = PersonalityBot(
            model_path="./mistral_qlora_finetuned",
            logger=self.logger
        )

        # Initialize tweet generator
        self.tweet_generator = TweetGenerator(personality_bot, logger=self.logger)
        
        # Initialize Stable Diffusion pipeline
        self.logger.info("Initializing Stable Diffusion pipeline...")
        self.pipe = self._initialize_diffusion_pipeline()
        
        # Pass pipe and api to ReplyHandler
        self.reply_handler = ReplyHandler(
            self.client, 
            self.tweet_generator, 
            logger=self.logger,
            pipe=self.pipe,
            api=self.api
        )

        self.meme_handler = MemeHandler(client=self.client, api=self.api, logger=self.logger)
        self.news_service = NewsService(logger=self.logger)

    def _initialize_diffusion_pipeline(self):
        """Initialize and return the Stable Diffusion pipeline with 8-bit text encoder."""
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
        ).to("cuda")

        # Convert text encoder weights to 8-bit
        for name, module in pipe.text_encoder.named_modules():
            if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
                module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)
        
        return pipe

    def _validate_env_variables(self) -> None:
        """Ensure all required environment variables are set."""
        required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def post_news(self) -> Optional[str]:
        """Post a news summary tweet if there's new content."""
        try:
            self.logger.info("Checking for latest crypto news...")
            article = self.news_service.get_latest_article()
            
            if not article:
                self.logger.info("No new articles found")
                return None
                    
            self.logger.info(f"Found article: {article.title}")
            article.content = self.news_service.get_article_content(article.url)
            
            if not article.content:
                self.logger.warning("Could not extract article content")
                return None
            
            # Generate summary prompt with Athena's personality
            prompt = (
                "System: You are Athena (@Athena_TBALL), the sassy crypto queen. "
                "Summarize this SPECIFIC news article with your signature style.\n\n"
                f"Article:\n"
                f"Title: {article.title}\n"
                f"Content: {article.content[:800]}\n\n"
                f"Create a tweet that:\n"
                f"1. MUST directly address the specific news from the article\n"
                f"2. MUST be between 80-240 characters\n"
                f"3. MUST include your reaction to this exact news\n"
                f"4. MUST mention any relevant market terms from the article\n"
                f"5. MUST use emojis (📈💰🏦🚀✨)\n\n"
                f"Example format:\n"
                f"[Your reaction to THIS news] + [Key points from THIS article] + [Emoji] + [Relevant hashtag] + ✨\n\n"
                f"Remember: Stay on topic about THIS specific news article!\n\n"
                "You MUST reference specific details from the article. Do NOT give generic responses!"
            )
            
            summary = self.tweet_generator.generate_tweet(prompt)
            
            if not summary:
                self.logger.warning("Could not generate summary")
                return None
            
            # Append the URL to the summary
            tweet_text = f"{summary}\n\n{article.url}"
            
            # Post the tweet
            result = self.client.create_tweet(text=tweet_text)
            if result and result.data.get('id'):
                # Mark the article as posted only after successful tweet
                self.news_service.mark_as_posted(article)
                # Clean up old entries periodically
                self.news_service.cleanup_old_entries()
                self.logger.info("Successfully posted news summary")
                return result.data.get('id')
            
            return None
                
        except Exception as e:
            self.logger.error(f"Error posting news: {str(e)}", exc_info=True)
            return None

    def post_tweet(self) -> Optional[str]:
        """Post a new tweet - randomly choose between news, meme, or text."""
        self.logger.info("Starting tweet posting process...")
        
        try:
            # Randomly decide content type
            roll = random.random()
            
            # Try news (15% chance)
            if roll < NEWS_POSTING_CHANCE:
                self.logger.info("Rolling for news post...")
                tweet_id = self.post_news()
                if tweet_id:
                    return tweet_id
                self.logger.info("No news to post, falling back to regular content")
            
            # Try meme (20% chance)
            elif roll < (NEWS_POSTING_CHANCE + MEME_POSTING_CHANCE):
                self.logger.info("Rolling for meme post...")
                tweet_id = self.meme_handler.post_meme()
                if tweet_id:
                    return tweet_id
                self.logger.warning("Meme posting failed, falling back to text tweet")
            
            # Handle text tweet (65% chance, or fallback)
            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]
            
            # Try prompts up to MAX_PROMPT_ATTEMPTS times
            for attempt in range(MAX_PROMPT_ATTEMPTS):
                if not all_prompts:
                    break
                    
                prompt = random.choice(all_prompts)
                all_prompts.remove(prompt)
                
                self.logger.info(f"Trying prompt {attempt + 1}/{MAX_PROMPT_ATTEMPTS}: {prompt}")
                tweet = self.tweet_generator.generate_tweet(prompt)
                
                if tweet:
                    result = self.client.create_tweet(text=tweet)
                    return result.data.get('id')
                    
                self.logger.warning("Tweet generation failed, trying next prompt...")
            
            # If all else fails, use fallback
            tweet = random.choice(FALLBACK_TWEETS)
            self.logger.info(f"Using fallback tweet: {tweet}")
            result = self.client.create_tweet(text=tweet)
            return result.data.get('id')

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
            return None
    
    def run(self):
        """Main bot running loop."""
        posted_tweet_ids = []  # Track all tweets for reply monitoring

        while True:
            try:
                self.logger.info("Starting new bot cycle...")
                tweet_id = self.post_tweet()
                
                if tweet_id:
                    self.logger.info(f"Posted tweet: {tweet_id}")
                    posted_tweet_ids.append(tweet_id)
                    
                    # Monitor replies for all tweets
                    self.reply_handler.monitor_tweets(posted_tweet_ids)
                    
                    # After monitoring, move to next cycle
                    self.logger.info("Reply monitoring complete")
                    
                    # Sleep before next cycle
                    time.sleep(POST_COOLDOWN)
                else:
                    self.logger.error("Tweet posting failed. Retrying after delay...")
                    time.sleep(RETRY_DELAY)

            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                self.logger.info(f"Retrying after {RETRY_DELAY // 60} minutes...")
                time.sleep(RETRY_DELAY)

def main():
    """Main entry point for the bot."""
    try:
        # Updated warnings for Mistral model
        warnings.filterwarnings("ignore", message=".*The model weights are not tied.*")
        warnings.filterwarnings("ignore", message=".*You are using a model that was converted to safetensors.*")
        warnings.filterwarnings("ignore", message=".*You have modified the pretrained model configuration.*")
        warnings.filterwarnings("ignore", message=".*Consider increasing the value of the max_position_embeddings attribute.*")
        warnings.filterwarnings("ignore", category=UserWarning)

        # Load environment variables
        load_dotenv()
        
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()
