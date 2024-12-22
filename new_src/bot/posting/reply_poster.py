import time
import logging
import os
from typing import Optional, List
from bot.configs.posting_config import (
    REPLY_DELAY_SECONDS,
    INITIAL_REPLY_DELAY,
    REPLY_CYCLE_DELAY,
    REPLY_CYCLES,
    FINAL_CHECK_DELAY,
)
from .utils import apply_delay, search_replies_to_tweet
from .state_manager import StateManager
from .prompt_extractor import extract_prompt
from .image_responder import ImageResponder
from bot.services.conversation_manager import ConversationManager

class ReplyPoster:
    def __init__(self, client, tweet_generator, logger=None, state_file="reply_state.json", pipe=None, api=None):
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")
        self.state_manager = StateManager(state_file, self.logger)
        self.image_responder = ImageResponder(pipe, api, self.logger)
        self.conversation_manager = ConversationManager(max_history_length=5)

    def _is_image_request(self, text: str) -> bool:
        text_lower = text.lower()
        # Return True only if the user explicitly requests an image
        return (
            "generate an image" in text_lower or
            "make an image" in text_lower or
            "create an image" in text_lower
        )

    def _handle_image_reply(self, reply, conversation_id: str):
        # Since we've confirmed it's an image request, now extract the prompt
        prompt = extract_prompt(reply.text)
        if prompt and prompt != reply.text:
            self.image_responder.reply_with_image(self.client, prompt, reply.id)
            self.conversation_manager.add_message(conversation_id, "Bot: [Image Response]")
        else:
            # If no prompt was extracted, treat it as a general request without a specific prompt
            # or simply log that no detailed prompt was provided.
            self.logger.info("Image request detected but no prompt extracted.")

    def _handle_text_reply(self, reply, conversation_id: str):
        conversation_history = self.conversation_manager.get_history(conversation_id)
        response = self.tweet_generator.generate_tweet(reply.text, conversation_history=conversation_history)
        if response:
            self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
            self.logger.info(f"Replied to tweet ID: {reply.id}.")
            self.conversation_manager.add_message(conversation_id, f"Bot: {response}")
        else:
            self.logger.warning(f"Generated response was empty for reply ID: {reply.id}.")

    def _process_single_reply(self, reply, max_reply_id_numeric):
        if reply.id <= max_reply_id_numeric:
            self.logger.info(f"Skipping already processed reply ID: {reply.id}.")
            return max_reply_id_numeric

        self.logger.info(f"Processing reply: {reply.text}.")
        conversation_id = str(reply.conversation_id)
        self.conversation_manager.add_message(conversation_id, f"User: {reply.text}")

        # Use the new _is_image_request() logic
        if self._is_image_request(reply.text):
            self._handle_image_reply(reply, conversation_id)
        else:
            self._handle_text_reply(reply, conversation_id)

        return max(max_reply_id_numeric, reply.id)

    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        replies = search_replies_to_tweet(self.client, tweet_id, self.bot_user_id, since_id, logger=self.logger)
        if not replies:
            self.logger.info(f"No new replies found for tweet ID {tweet_id}.")
            return since_id

        max_reply_id_numeric = int(since_id) if since_id and since_id.isdigit() else 0
        for reply in sorted(replies, key=lambda x: x.id):
            try:
                max_reply_id_numeric = self._process_single_reply(reply, max_reply_id_numeric)
                self.state_manager.save_state()
                time.sleep(REPLY_DELAY_SECONDS)
            except Exception:
                self.logger.exception(f"Error processing reply {reply.id}.")

        return str(max_reply_id_numeric) if max_reply_id_numeric else since_id

    def monitor_tweets(self, tweet_ids: List[str]):
        delays = [INITIAL_REPLY_DELAY] + [REPLY_CYCLE_DELAY] * REPLY_CYCLES + [FINAL_CHECK_DELAY]
        self.logger.info(f"Monitoring tweets: {tweet_ids}")

        for tweet_id in tweet_ids:
            if tweet_id not in self.state_manager.last_processed_ids:
                self.state_manager.last_processed_ids[tweet_id] = None

        for delay in delays:
            apply_delay(delay, self.logger)
            for tweet_id in tweet_ids:
                since_id = self.state_manager.last_processed_ids.get(tweet_id)
                new_since_id = self.process_replies(tweet_id, since_id)
                if new_since_id:
                    self.state_manager.last_processed_ids[tweet_id] = new_since_id

        self.logger.info("Reply monitoring complete for all tweets.")
        self.state_manager.save_state()
