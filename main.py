import os
import re
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
from bot.services.news.news_service import NewsService
from bot.configs.posting_config import (
    POST_COOLDOWN,
    RETRY_DELAY,
    MAX_PROMPT_ATTEMPTS,
    NEWS_POSTING_CHANCE,
    MEME_POSTING_CHANCE
)

import torch
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline

class TwitterBot:
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Starting the bot...")
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        self._validate_env_variables()
        
        self.client = setup_twitter_client()
        self.api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))
        self.rate_limit_tracker = RateLimitTracker()
        
        personality_bot = PersonalityBot(
            model_path="./mistral_qlora_finetuned",
            logger=self.logger
        )

        self.tweet_generator = TweetGenerator(personality_bot, logger=self.logger)
        
        self.logger.info("Initializing Stable Diffusion pipeline...")
        self.pipe = self._initialize_diffusion_pipeline()
        
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
        pipe = StableDiffusionPipeline.from_pretrained(
            "./sd2_model", torch_dtype=torch.float16
        ).to("cuda")

        for name, module in pipe.text_encoder.named_modules():
            if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
                module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)
        
        return pipe

    def _validate_env_variables(self) -> None:
        required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _get_news_prompt(self, article) -> str:
        return (
            "System: Generate a sassy crypto tweet about this news. REQUIREMENTS:\n"
            "1. MUST end with either 💅 or ✨ (no exceptions)\n"
            "2. MUST include #CryptoNewsQueen\n"
            "3. MUST include numbers from article\n"
            "4. Maximum 180 characters\n\n"
            f"Article: {article.title}\n"
            f"Key Stats: {article.content[:200]}\n\n"
            "Example Format:\n"
            '"[Your sassy take with stats] #CryptoNewsQueen 💅"\n\n'
            "Tweet:"
        )

    def _validate_news_tweet(self, tweet: str, article_title: str, article_content: str) -> bool:
        """Validates tweet against specific criteria with detailed logging."""
        if not tweet or len(tweet.strip()) == 0:
            self.logger.debug("Tweet is empty")
            return False
            
        if len(tweet) > 180:
            self.logger.debug(f"Tweet too long: {len(tweet)} chars")
            return False
            
        # Check for required emoji ending
        if not tweet.strip().endswith('💅') and not tweet.strip().endswith('✨'):
            self.logger.debug("Tweet missing required emoji ending")
            return False
            
        # Check for required hashtag
        if '#CryptoNewsQueen' not in tweet:
            self.logger.debug("Tweet missing #CryptoNewsQueen hashtag")
            return False
            
        # Check for numbers from article
        if not re.search(r'\d+%|\$\d+|\d{2,}', tweet):
            self.logger.debug("Tweet missing required numbers")
            return False
            
        return True

    def _format_news_tweet(self, tweet: str) -> str:
        """Ensures tweet meets formatting requirements."""
        tweet = tweet.strip()
        
        # Add hashtag if missing
        if '#CryptoNewsQueen' not in tweet:
            tweet = tweet.rstrip('💅✨') + ' #CryptoNewsQueen'
        
        # Ensure proper emoji ending
        if not tweet.endswith('💅') and not tweet.endswith('✨'):
            tweet += ' 💅'
            
        # Truncate if too long
        if len(tweet) > 180:
            # Find last space before 180 chars
            space_idx = tweet[:177].rfind(' ')
            if space_idx != -1:
                tweet = tweet[:space_idx] + ' 💅'
            else:
                tweet = tweet[:177] + ' 💅'
                
        return tweet

    def post_news(self) -> Optional[str]:
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
            
            max_attempts = 3
            for attempt in range(max_attempts):
                self.logger.info(f"Generating tweet, attempt {attempt + 1}/{max_attempts}...")
                prompt = self._get_news_prompt(article)
                candidate = self.tweet_generator.generate_tweet(prompt)
                
                # Log raw candidate
                self.logger.debug(f"Raw candidate: {candidate}")
                
                # Format the tweet
                formatted_tweet = self._format_news_tweet(candidate)
                self.logger.debug(f"Formatted tweet: {formatted_tweet}")
                
                if self._validate_news_tweet(formatted_tweet, article.title, article.content):
                    try:
                        result = self.client.create_tweet(text=formatted_tweet)
                        if result and result.data.get('id'):
                            self.news_service.mark_as_posted(article)
                            self.news_service.cleanup_old_entries()
                            self.logger.info(f"Posted news tweet: {formatted_tweet}")
                            return result.data.get('id')
                    except Exception as e:
                        self.logger.error(f"Failed to post tweet: {str(e)}")
                        continue
            
            self.logger.warning("Could not generate valid news tweet after all attempts")
            return None
                
        except Exception as e:
            self.logger.error(f"Error posting news: {str(e)}", exc_info=True)
            return None

    def post_tweet(self) -> Optional[str]:
        """Post a new tweet - randomly choose between news, meme, or text."""
        self.logger.info("Starting tweet posting process...")
        
        try:
            roll = random.random()
            
            if roll < NEWS_POSTING_CHANCE:
                self.logger.info("Rolling for news post...")
                tweet_id = self.post_news()
                if tweet_id:
                    return tweet_id
                self.logger.info("No news to post, falling back to regular content")
            
            elif roll < (NEWS_POSTING_CHANCE + MEME_POSTING_CHANCE):
                self.logger.info("Rolling for meme post...")
                tweet_id = self.meme_handler.post_meme()
                if tweet_id:
                    return tweet_id
                self.logger.warning("Meme posting failed, falling back to text tweet")
            
            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]
            
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
            
            tweet = random.choice(FALLBACK_TWEETS)
            self.logger.info(f"Using fallback tweet: {tweet}")
            result = self.client.create_tweet(text=tweet)
            return result.data.get('id')

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
            return None
    
    def run(self):
        posted_tweet_ids = []

        while True:
            try:
                self.logger.info("Starting new bot cycle...")
                tweet_id = self.post_tweet()
                
                if tweet_id:
                    self.logger.info(f"Posted tweet: {tweet_id}")
                    posted_tweet_ids.append(tweet_id)
                    
                    self.reply_handler.monitor_tweets(posted_tweet_ids)
                    
                    self.logger.info("Reply monitoring complete")
                    self.logger.info(f"Entering cooldown for {POST_COOLDOWN} seconds before starting next cycle...")
                    time.sleep(POST_COOLDOWN)
                else:
                    self.logger.error("Tweet posting failed. Retrying after delay...")
                    time.sleep(RETRY_DELAY)

            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                self.logger.info(f"Retrying after {RETRY_DELAY // 60} minutes...")
                time.sleep(RETRY_DELAY)

def main():
    try:
        warnings.filterwarnings("ignore", message=".*The model weights are not tied.*")
        warnings.filterwarnings("ignore", message=".*You are using a model that was converted to safetensors.*")
        warnings.filterwarnings("ignore", message=".*You have modified the pretrained model configuration.*")
        warnings.filterwarnings("ignore", message=".*Consider increasing the value of the max_position_embeddings attribute.*")
        warnings.filterwarnings("ignore", category=UserWarning)

        load_dotenv()
        
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()