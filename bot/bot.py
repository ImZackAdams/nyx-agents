"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

from typing import List, Optional, Tuple
import random

from .text_processor import (
    TextProcessor,
    StyleConfig,
    Category,
    ContentAnalyzer
)
from .utilities import log_resource_usage
from .model_config import ModelManager
from .prompt_templates import PromptManager, PersonalityConfig
from .prompts import get_all_prompts

class PersonalityBot:
    def __init__(self, model_path: str, logger, style_config: Optional[StyleConfig] = None, max_retries: int = 3):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
            style_config: Optional custom style configuration
            max_retries: Maximum number of generation attempts before falling back
        """
        self.logger = logger
        self.model_manager = ModelManager(model_path, logger)
        self.max_retries = max_retries
        
        # Response history management
        self.max_history: int = 10
        self.recent_responses: List[str] = []
        
        # Character limits
        self.min_chars = 180
        self.max_chars = 220
        
        # Initialize processors
        self.style_config = style_config or StyleConfig.default()
        self.text_processor = TextProcessor(self.style_config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        self.prompt_manager = PromptManager()

        # Initialize fallback tweets
        self.all_prompts = get_all_prompts()
        self.fallback_tweets = [tweet for tweet in self.all_prompts['fallback_tweets'] 
                              if self.min_chars <= len(tweet.strip()) <= self.max_chars]
        
        if not self.fallback_tweets:
            # If no fallbacks meet length requirements, pad or truncate them
            self.fallback_tweets = []
            for tweet in self.all_prompts['fallback_tweets']:
                padded_tweet = self._adjust_tweet_length(tweet)
                if padded_tweet:
                    self.fallback_tweets.append(padded_tweet)

    def _validate_tweet_length(self, tweet: str) -> bool:
        """Check if tweet meets length requirements (180-220 characters)."""
        clean_length = len(tweet.strip())
        return self.min_chars <= clean_length <= self.max_chars

    def _adjust_tweet_length(self, tweet: str) -> Optional[str]:
        """Adjust tweet length to meet requirements by padding or truncating."""
        clean_tweet = tweet.strip()
        length = len(clean_tweet)
        
        if length > self.max_chars:
            # Truncate to max_chars - 3 to account for ellipsis
            truncated = clean_tweet[:(self.max_chars - 3)].rsplit(' ', 1)[0]
            return f"{truncated}..."
        elif length < self.min_chars:
            # Pad with relevant hashtags from a predefined list
            crypto_hashtags = ["#crypto", "#defi", "#bitcoin", "#eth", "#finance", "#trading"]
            padded = clean_tweet
            while len(padded) < self.min_chars and crypto_hashtags:
                hashtag = random.choice(crypto_hashtags)
                crypto_hashtags.remove(hashtag)
                padded = f"{padded} {hashtag}"
            if self.min_chars <= len(padded) <= self.max_chars:
                return padded
            return None
        return clean_tweet

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
        return self.model_manager.generate(context)

    def _store_response(self, response: str) -> None:
        """Store the response in history to avoid repetition."""
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.max_history:
            self.recent_responses.pop(0)

    def _prepare_context(self, prompt: str, sentiment: str, category: Category, attempt: int) -> str:
        """
        Prepare the context for response generation.
        Adjusts the context based on retry attempt.
        """
        opener = random.choice([op for op in self.style_config.openers 
                              if op not in self.text_processor.recent_openers])
        
        context = self.prompt_manager.build_prompt(
            user_prompt=prompt,
            opener=opener,
            sentiment=sentiment,
            category=category
        )
        
        # Add length guidance based on attempt
        if attempt == 0:
            return context + f" Response must be between {self.min_chars} and {self.max_chars} characters."
        elif attempt == 1:
            return context + f" Response must be detailed, between {self.min_chars}-{self.max_chars} characters."
        else:
            return context + f" Response MUST be exactly within {self.min_chars}-{self.max_chars} characters. Add relevant hashtags if needed."

    def _try_generate_valid_response(self, prompt: str, sentiment: str, category: Category) -> Tuple[bool, str]:
        """
        Attempt to generate a valid response with retries.
        Returns (success, response) tuple.
        """
        for attempt in range(self.max_retries):
            try:
                # Generate context with attempt-specific guidance
                context = self._prepare_context(prompt, sentiment, category, attempt)
                self.logger.info(f"Attempt {attempt + 1}: Generated context: {context}")
                
                # Generate and process response
                generated_text = self._generate_model_response(context)
                if not generated_text:
                    continue
                
                response = self.text_processor.process_tweet(prompt, generated_text)
                
                # Try to adjust length if needed
                if not self._validate_tweet_length(response):
                    adjusted_response = self._adjust_tweet_length(response)
                    if not adjusted_response or not self._validate_tweet_length(adjusted_response):
                        continue
                    response = adjusted_response
                
                return True, response
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                continue
        
        return False, ""

    def _get_fallback_response(self) -> str:
        """Get a random fallback response that hasn't been used recently."""
        available_responses = [resp for resp in self.fallback_tweets 
                             if resp not in self.recent_responses]
        
        if not available_responses:
            available_responses = self.fallback_tweets
            
        return random.choice(available_responses)

    def generate_response(self, prompt: str) -> str:
        """Generate a Twitter-ready response based on the given prompt."""
        if not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        try:
            # Analyze input
            sentiment = self.content_analyzer.analyze_sentiment(prompt)
            category = self.content_analyzer.categorize_prompt(prompt)
            
            # Try to generate a valid response with retries
            success, response = self._try_generate_valid_response(prompt, sentiment, category)
            
            if success:
                self._store_response(response)
                return response
            
            # Fall back if all attempts failed
            self.logger.warning(f"All {self.max_retries} generation attempts failed, using fallback")
            fallback = self._get_fallback_response()
            self._store_response(fallback)
            return fallback

        except Exception as e:
            self.logger.error(f"Error in response generation pipeline: {e}")
            fallback = self._get_fallback_response()
            self._store_response(fallback)
            return fallback