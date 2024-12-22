# new_src/bot/posting/tweet_generator.py

import random
import logging
from typing import Optional, List

# UPDATED IMPORTS FOR NEW STRUCTURE:
from utils.text.text_cleaner import TextCleaner
from bot.prompts import FALLBACK_TWEETS
from config.posting_config import (
    MAX_TWEET_LENGTH,
    MIN_TWEET_LENGTH,
    MAX_GENERATION_ATTEMPTS,
)
from config.personality_config import AthenaPersonalityConfig


def validate_tweet(tweet: str) -> bool:
    """Validate the tweet's length and content."""
    return MIN_TWEET_LENGTH <= len(tweet) <= MAX_TWEET_LENGTH


class TweetGenerator:
    def __init__(self, personality_bot, cleaner=None, logger=None):
        self.bot = personality_bot
        self.cleaner = cleaner or TextCleaner()
        self.logger = logger or logging.getLogger(__name__)

        # Load the personality config if needed
        self.personality_config = AthenaPersonalityConfig.default()

    def generate_tweet(
        self,
        user_message: str,
        conversation_history: Optional[List[str]] = None
    ) -> str:
        """
        Generate a tweet response with a structured prompt for Mistral 7B Instruct.
        
        :param user_message: The latest user message.
        :param conversation_history: A list of previous turns, e.g.:
                                     ["User: Hello Athena!", 
                                      "Bot: Hey bestie! ✨", 
                                      "User: How are you today?"]
        """

        # System message providing the style and constraints
        system_message = (
            "### System:\n"
            "You are Athena (@Athena_TBALL), a witty, sassy Twitter bot who remembers "
            "the previous conversation. Respond in short, coherent tweets between "
            f"{MIN_TWEET_LENGTH} and {MAX_TWEET_LENGTH} chars. Use no more than 2 hashtags "
            "and add ✨sass✨. End with a flourish (💅 or ✨).\n\n"
            f"{self.personality_config.DEFAULT_PERSONALITY}\n"
        )

        # Format the conversation history
        history_str = ""
        if conversation_history and len(conversation_history) > 0:
            history_str = "### Conversation History:\n" + "\n".join(conversation_history)

        # Current user prompt
        user_section = f"### User:\n{user_message}"

        # Assistant (Bot) response section - the model should continue here
        assistant_section = "### Assistant (Bot):"

        # Combine all parts into a final prompt
        combined_prompt = (
            f"{system_message}\n{history_str}\n\n{user_section}\n\n{assistant_section}"
        )

        for attempt in range(MAX_GENERATION_ATTEMPTS):
            try:
                self.logger.info(f"Generating tweet, attempt {attempt + 1}...")
                self.logger.debug(f"Final prompt:\n{combined_prompt}")
                
                response = self.bot.generate_response(combined_prompt)
                cleaned_response = self.cleaner.clean_text(response)

                if len(cleaned_response) > MAX_TWEET_LENGTH:
                    self.logger.warning(
                        f"Generated tweet too long ({len(cleaned_response)} chars). "
                        "Truncating..."
                    )
                    cleaned_response = cleaned_response[:MAX_TWEET_LENGTH].strip()

                if validate_tweet(cleaned_response):
                    self.logger.info(
                        f"Generated valid tweet: {cleaned_response} "
                        f"({len(cleaned_response)} chars)"
                    )
                    return cleaned_response
                else:
                    self.logger.warning(
                        f"Generated tweet invalid: {cleaned_response} "
                        f"({len(cleaned_response)} chars)"
                    )
            except Exception as e:
                self.logger.warning(f"Error generating tweet: {e}", exc_info=True)

        # If all attempts fail, use a fallback tweet
        fallback_tweet = random.choice(FALLBACK_TWEETS)
        self.logger.info(f"Using fallback tweet: {fallback_tweet}")
        return fallback_tweet
