"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

from typing import List, Optional
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
    def __init__(self, model_path: str, logger, style_config: Optional[StyleConfig] = None):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
            style_config: Optional custom style configuration
        """
        self.logger = logger
        self.model_manager = ModelManager(model_path, logger)
        
        # Response history management
        self.max_history: int = 10
        self.recent_responses: List[str] = []
        
        # Initialize processors
        self.style_config = style_config or StyleConfig.default()
        self.text_processor = TextProcessor(self.style_config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        self.prompt_manager = PromptManager()

        # Initialize fallback tweets
        self.all_prompts = get_all_prompts()
        self.fallback_tweets = self.all_prompts['fallback_tweets']

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
        return self.model_manager.generate(context)

    def _store_response(self, response: str) -> None:
        """Store the response in history to avoid repetition."""
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.max_history:
            self.recent_responses.pop(0)

    def _prepare_context(self, prompt: str, sentiment: str, category: Category) -> str:
        """Prepare the context for response generation."""
        opener = random.choice([op for op in self.style_config.openers 
                              if op not in self.text_processor.recent_openers])
        
        return self.prompt_manager.build_prompt(
            user_prompt=prompt,
            opener=opener,
            sentiment=sentiment,
            category=category
        )

    def _validate_tweet_length(self, tweet: str) -> bool:
        """Check if tweet meets length requirements."""
        clean_length = len(tweet.strip())
        return 50 <= clean_length <= 240

    def _get_fallback_response(self) -> str:
        """Get a random fallback response that hasn't been used recently."""
        available_responses = [resp for resp in self.fallback_tweets 
                             if resp not in self.recent_responses]
        
        if not available_responses:
            # If all fallbacks have been used, clear history and use any
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
            
            # Generate context
            context = self._prepare_context(prompt, sentiment, category)
            self.logger.info(f"Generated context: {context}")

            # Generate response
            generated_text = self._generate_model_response(context)
            if not generated_text:
                fallback = self._get_fallback_response()
                self._store_response(fallback)
                return fallback
            
            self.logger.info(f"Generated raw response: {generated_text}")

            # Format response using TextProcessor
            response = self.text_processor.process_tweet(prompt, generated_text)
            
            # Validate and store
            if self._validate_tweet_length(response):
                self._store_response(response)
                return response
            else:
                self.logger.warning("Generated response failed length validation")
                fallback = self._get_fallback_response()
                self._store_response(fallback)
                return fallback

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            fallback = self._get_fallback_response()
            self._store_response(fallback)
            return fallback