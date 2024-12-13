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

    import re

    def _extract_prompt(self, text: str) -> str:
        """
        Extracts the prompt from the user's message by identifying a wide range of trigger phrases
        that indicate the user wants to generate an image or something visually represented.

        The function:
        - Strips out bot mentions (e.g., "@YourBot")
        - Looks for any combination of synonyms and phrases that mean:
        "generate/make/create/show/draw/render/illustrate/etc. me an/a/the image/picture/photo/etc. of/about X"
        - Returns the substring after that trigger phrase as the prompt.

        Examples:
        "@YourBot Please generate an image of a golden retriever playing chess"
            => "a golden retriever playing chess"

        "@YourBot Could you show me a picture featuring a futuristic city?"
            => "a futuristic city"

        "make me a drawing of an alien landscape"
            => "an alien landscape"

        Customization:
        To add or remove synonyms, simply update `verb_synonyms` or `image_synonyms`.
        """

        # Remove bot mentions
        text = re.sub(r"@\w+", "", text).strip()

        # Define sets of synonyms. We use a large set to cover many user phrasings.
        # The pattern aims to capture phrases like:
        # - generate me an image of
        # - create a picture about
        # - show me a photo featuring
        # - produce an illustration depicting
        # - etc.
        verb_synonyms = (
            "generate", "make", "create", "produce", "show", "render", "draw", 
            "illustrate", "visualize", "depict", "design", "conjure", "whip(?: up)?", 
            "come up with", "show me", "give me", "get me", "craft"
        )
        image_synonyms = (
            "image", "picture", "photo", "artwork", "drawing", "illustration", 
            "sketch", "graphic", "portrait", "photograph"
        )
        
        # Prepositions or linking words that might appear after "image/picture"
        # like "of", "about", "featuring", "depicting".
        # This makes the pattern more flexible.
        linking_words = "(?:of|about|featuring|depicting|showing|portraying)?"

        # Optional words before the noun: e.g., "an image", "a picture", "the photo"
        optional_articles = "(?:me )?(?:an? |the )?"

        # Build the regex pattern dynamically from synonyms
        # We join them using `|` to create a single capturing group that can match any synonym.
        verb_pattern = "(?:" + "|".join(verb_synonyms) + ")"
        image_pattern = "(?:" + "|".join(image_synonyms) + ")"

        # Construct the full trigger pattern:
        # Explanation:
        # - `verb_pattern`: Matches any of the verb synonyms.
        # - `(?: me)?`: The word "me" might appear after the verb, e.g., "show me".
        # - `optional_articles`: Matches optional "me", "an", "a", or "the".
        # - `image_pattern`: Matches any of the image synonyms.
        # - `(?: " + linking_words + ")`: Matches an optional linking word (of, about, featuring...)
        # - We allow some whitespace flexibility `\s+` around optional parts.
        trigger_regex = rf"({verb_pattern})\s*(?:me\s*)?(?:an?\s*|the\s*)?({image_pattern})\s*(?:{linking_words})\s*"

        # Compile the regex as case-insensitive.
        trigger_pattern = re.compile(trigger_regex, re.IGNORECASE)

        # Search for the first occurrence of the trigger phrase in the text
        match = trigger_pattern.search(text)
        if match:
            # Extract everything after the matched phrase
            # `match.end()` gives the index in `text` right after the matched portion.
            prompt_part = text[match.end():].strip()
            return prompt_part

        # If no trigger was found, we can simply return the original text as a fallback,
        # or handle it differently if needed.
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

        reply_text = ""
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
