"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

from typing import List, Optional, Tuple
import random
from bot.processors.text_processor import TextProcessor
from bot.processors.content_analyzer import ContentAnalyzer
from bot.processors.prompt_templates import PromptManager
# Replace import from style_config with personality_config
from bot.configs.personality_config import AthenaPersonalityConfig, Category
from bot.utilities.resource_monitor import log_resource_usage

from bot.configs.model_config import ModelManager
from bot.configs.posting_config import MAX_TWEET_LENGTH, MIN_TWEET_LENGTH


class PersonalityBot:
    def __init__(self, model_path: str, logger, config: Optional[AthenaPersonalityConfig] = None):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
            config: Optional custom AthenaPersonalityConfig
        """
        self.logger = logger
        self.model_manager = ModelManager(model_path, logger)
        
        # Set max history first
        self.max_history = 10
        
        # Initialize processors
        self.config = config or AthenaPersonalityConfig.default()
        self.text_processor = TextProcessor(self.config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        self.prompt_manager = PromptManager(self.config)
        
        # Initialize opener history
        self.text_processor.recent_openers = []

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
        return self.model_manager.generate(context)

    def _prepare_context(self, prompt: str, sentiment: str, category: Category) -> str:
        """Prepare the context for response generation."""
        opener = random.choice([
            op for op in self.config.openers
            if op not in self.text_processor.recent_openers
        ])
        
        # Add opener to history
        self.text_processor.recent_openers.append(opener)
        if len(self.text_processor.recent_openers) > self.max_history:
            self.text_processor.recent_openers.pop(0)
        
        context = self.prompt_manager.build_prompt(
            user_prompt=prompt,
            opener=opener,
            sentiment=sentiment,
            category=category
        )
        
        return (
            f"System: Response must be detailed and between {MIN_TWEET_LENGTH}-{MAX_TWEET_LENGTH} characters. "
            "Include hashtags and emojis.\n"
            f"User: {context}"
        )

    def generate_response(self, prompt: str) -> str:
        """Generate a response based on the given prompt."""
        if not prompt.strip():
            return ""

        try:
            # Analyze input
            sentiment = self.content_analyzer.analyze_sentiment(prompt)
            category = self.content_analyzer.categorize_prompt(prompt)
            
            # Generate context
            context = self._prepare_context(prompt, sentiment, category)
            self.logger.info(f"Generated context: {context}")
            
            # Generate and process response
            generated_text = self._generate_model_response(context)
            if not generated_text:
                return ""
            
            self.logger.info(f"Generated raw response: {generated_text}")
            
            # Format response using TextProcessor and remove any system instructions
            processed_text, error = self.text_processor.process_tweet(prompt, generated_text)
            if error:
                self.logger.error(f"Error processing tweet: {error}")
                return ""
            
            if processed_text:
                system_instruction = (
                    f"System: Response must be detailed and between {MIN_TWEET_LENGTH}-{MAX_TWEET_LENGTH} "
                    "characters. Include hashtags and emojis."
                )
                return processed_text.replace(system_instruction, "").strip()
            
            return ""

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""
