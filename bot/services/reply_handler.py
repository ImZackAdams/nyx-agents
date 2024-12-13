import time
import logging
import os
import json
import re
from typing import Optional, List, Dict
from bot.configs.posting_config import (
    REPLY_DELAY_SECONDS,
    INITIAL_REPLY_DELAY,
    REPLY_CYCLE_DELAY,
    REPLY_CYCLES,
    FINAL_CHECK_DELAY,
)


def apply_delay(duration, logger=None):
    """Apply a delay and log it."""
    if logger:
        logger.info(f"Waiting {duration // 60} minutes...")
    time.sleep(duration)


def search_replies_to_tweet(client, tweet_id, bot_user_id, since_id=None, logger=None):
    """Search replies to a specific tweet, excluding those from the bot."""
    query = f"conversation_id:{tweet_id} -from:{bot_user_id}"

    try:
        results = client.search_recent_tweets(
            query=query,
            tweet_fields=["author_id", "text", "id"],
            since_id=since_id
        )
        return results.data or []
    except Exception as e:
        if logger:
            logger.error(f"Failed to fetch replies for tweet ID {tweet_id}.", exc_info=True)
        return []


class ReplyHandler:
    def __init__(self, client, tweet_generator, logger=None, state_file="reply_state.json", pipe=None, api=None):
        """
        Initialize the ReplyHandler.

        :param client: Twitter API v2 client
        :param tweet_generator: Object with a generate_tweet(prompt: str) -> str method
        :param logger: Logger instance
        :param state_file: Path to a JSON file for storing state
        :param pipe: Stable Diffusion pipeline for image generation
        :param api: Tweepy API (for media_upload)
        """
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")
        self.state_file = state_file
        self.last_processed_ids = self._load_state()
        self.pipe = pipe
        self.api = api

    def _load_state(self) -> Dict[str, Optional[str]]:
        """Load the last processed IDs from a JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as file:
                    return json.load(file)
            except Exception as e:
                self.logger.error(f"Error loading state file: {e}")
        return {}

    def _save_state(self) -> None:
        """Save the last processed IDs to a JSON file."""
        try:
            with open(self.state_file, "w") as file:
                json.dump(self.last_processed_ids, file)
            self.logger.info("Reply state saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")

    def _is_image_request(self, text: str) -> bool:
        """
        Determine if the user's reply requests an image.
        Adjust this logic based on your preference.
        """
        text_lower = text.lower()
        return "generate image" in text_lower or "make an image" in text_lower

    def _extract_prompt(self, text: str) -> str:
        """
        Extract the prompt from the user's reply.
        Assumes the text contains a trigger phrase like "generate image" or "make an image".
        
        Example:
        "@YourBot Please generate image of a golden retriever playing chess"
        => prompt: "a golden retriever playing chess"
        """
        # Remove bot mentions
        text = re.sub(r"@\w+", "", text).strip()

        # Remove the trigger phrases
        triggers = ["generate image of", "generate image", "make an image of", "make an image"]
        for trigger in triggers:
            if trigger in text.lower():
                # Find the index where trigger phrase ends and extract the rest
                idx = text.lower().find(trigger)
                # Extract the substring after the trigger
                prompt_part = text[idx + len(trigger):].strip()
                return prompt_part

        # If no specific trigger found but we matched _is_image_request,
        # return the text after removing known phrases.
        return text

    def _reply_with_image(self, prompt: str, reply_to_tweet_id: str):
        """
        Generate an image using Stable Diffusion and reply to the tweet with the image attached.
        """
        if not self.pipe:
            self.logger.error("No Stable Diffusion pipeline available!")
            return

        self.logger.info(f"Generating image for prompt: {prompt}")
        image = self.pipe(prompt, num_inference_steps=30, guidance_scale=7.5).images[0]

        temp_filename = "generated_reply_image.png"
        image.save(temp_filename)

        self.logger.info("Uploading image to Twitter...")
        media = self.api.media_upload(temp_filename)
        
        if not media or not media.media_id:
            self.logger.error("Image upload failed.")
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return

        reply_text = "Here's your image! ✨"
        result = self.client.create_tweet(
            text=reply_text,
            media_ids=[media.media_id],
            in_reply_to_tweet_id=reply_to_tweet_id
        )

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        if result and result.data.get('id'):
            self.logger.info(f"Replied with image tweet ID: {result.data.get('id')}")
        else:
            self.logger.error("Failed to post reply with image.")

    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Process new replies for a single tweet and respond."""
        try:
            replies = search_replies_to_tweet(
                self.client, tweet_id, self.bot_user_id, since_id=since_id, logger=self.logger
            )
            if not replies:
                self.logger.info(f"No new replies found for tweet ID {tweet_id}.")
                return since_id

            # Track the maximum reply ID processed
            max_reply_id = since_id or "0"
            max_reply_id_numeric = int(max_reply_id) if max_reply_id.isdigit() else 0

            for reply in sorted(replies, key=lambda x: x.id):
                if reply.id <= max_reply_id_numeric:
                    self.logger.info(f"Skipping already processed reply ID: {reply.id} for tweet ID {tweet_id}.")
                    continue

                try:
                    self.logger.info(f"Processing reply: {reply.text} for tweet ID {tweet_id}.")

                    # Check if user requests an image
                    if self._is_image_request(reply.text):
                        prompt = self._extract_prompt(reply.text)
                        if prompt:
                            self._reply_with_image(prompt, reply.id)
                        else:
                            self.logger.info("Image request detected but no prompt extracted.")
                    else:
                        # Otherwise, handle text response
                        response = self.tweet_generator.generate_tweet(reply.text)
                        if response:
                            self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
                            self.logger.info(f"Replied to tweet ID: {reply.id} for original tweet {tweet_id}.")
                        else:
                            self.logger.warning(f"Generated response was empty for reply ID: {reply.id}.")

                    max_reply_id_numeric = max(max_reply_id_numeric, reply.id)
                    self._save_state()  # Persist state after updating
                    time.sleep(REPLY_DELAY_SECONDS)

                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {e}", exc_info=True)

            return str(max_reply_id_numeric)
        except Exception as e:
            self.logger.error(f"Error processing replies for tweet ID {tweet_id}: {e}", exc_info=True)
            return since_id

    def monitor_tweets(self, tweet_ids: List[str]):
        """Monitor multiple tweets for replies."""
        delays = [INITIAL_REPLY_DELAY] + [REPLY_CYCLE_DELAY] * REPLY_CYCLES + [FINAL_CHECK_DELAY]
        self.logger.info(f"Monitoring tweets: {tweet_ids}")

        # Ensure all tweet IDs are tracked
        for tweet_id in tweet_ids:
            if tweet_id not in self.last_processed_ids:
                self.last_processed_ids[tweet_id] = None

        for delay in delays:
            apply_delay(delay, self.logger)
            for tweet_id in tweet_ids:
                since_id = self.last_processed_ids.get(tweet_id)
                new_since_id = self.process_replies(tweet_id, since_id)
                if new_since_id:
                    self.last_processed_ids[tweet_id] = new_since_id

        self.logger.info("Reply monitoring complete for all tweets.")
        self._save_state()
