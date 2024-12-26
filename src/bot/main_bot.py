"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

from typing import Optional
import random
from utils.text.text_processor import TextProcessor
from utils.text.content_analyzer import ContentAnalyzer
from config.personality_config import AthenaPersonalityConfig
from utils.resource_monitor import log_resource_usage
from config.model_config import ModelManager
from config.posting_config import MAX_TWEET_LENGTH, MIN_TWEET_LENGTH
import logging


class PersonalityBot:
    def __init__(self, model_path: str, logger, config: Optional[AthenaPersonalityConfig] = None):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
            config: Optional custom AthenaPersonalityConfig
        """
        self.logger = logger or logging.getLogger(__name__)
        self.model_manager = ModelManager(model_path, self.logger)
        
        # Set max history (not strictly necessary if you're handling history elsewhere)
        self.max_history = 10
        
        # Initialize processors and config
        self.config = config or AthenaPersonalityConfig.default()
        self.text_processor = TextProcessor(self.config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        
        
        # Initialize opener history
        self.text_processor.recent_openers = []

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
        return self.model_manager.generate(context)

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response based on the given prompt.
        
        IMPORTANT: We now assume `prompt` is a fully formed prompt that includes:
        - A system message
        - Possibly conversation history
        - A 'User:' section
        - A final '### Assistant (Bot):' section where the model will continue

        This means we do NOT add system/user instructions here. 
        Just pass the prompt as-is to the model.
        """
        if not prompt.strip():
            return ""

        try:
            self.logger.info(f"Final prompt being sent to model:\n{prompt}")
            generated_text = self._generate_model_response(prompt)
            if not generated_text:
                return ""
            
            self.logger.info(f"Generated raw response: {generated_text}")
            
            # Process the tweet (if needed) to remove extraneous instructions
            # If your new prompt format doesn't include extraneous instructions in the output,
            # you might only need minimal cleaning.
            processed_text, error = self.text_processor.process_tweet("", generated_text)
            if error:
                self.logger.error(f"Error processing tweet: {error}")
                return ""
            
            if processed_text:
                # If the processed text still contains system instructions (it shouldn't now),
                # remove them. Adjust as necessary if you see system instructions in output.
                return processed_text.strip()
            
            return ""

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""
