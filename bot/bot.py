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
        
        # Set max history first
        self.max_history = 10
        
        # Initialize processors
        self.style_config = style_config or StyleConfig.default()
        self.text_processor = TextProcessor(self.style_config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        self.prompt_manager = PromptManager()
        
        # Initialize opener history
        self.text_processor.recent_openers = []

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
        return self.model_manager.generate(context)

    def _prepare_context(self, prompt: str, sentiment: str, category: Category) -> str:
        """Prepare the context for response generation."""
        opener = random.choice([op for op in self.style_config.openers 
                              if op not in self.text_processor.recent_openers])
        
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
        
        # Move constraints to a separate system instruction section
        return f"""System: Response must be detailed and between 180-220 characters. Include hashtags and emojis.
User: {context}"""

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
            processed_text = self.text_processor.process_tweet(prompt, generated_text)
            return processed_text.replace("System: Response must be detailed and between 180-220 characters. Include hashtags and emojis.", "").strip()

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""