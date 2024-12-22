import os
import random
import logging
from typing import Optional
from bot.prompts import MEME_CAPTIONS
from config.posting_config import (
    MEME_POSTING_CHANCE,
    SUPPORTED_MEME_FORMATS,
    MEMES_FOLDER_NAME,
)


def post_image_with_tweet(client, api, tweet_text, image_path, logger):
    """Posts a tweet with an image attachment."""
    try:
        media = api.media_upload(image_path)
        logger.info(f"Image uploaded. Media ID: {media.media_id}")

        result = client.create_tweet(
            text=tweet_text,
            media_ids=[str(media.media_id)],
        )
        logger.info("Tweet with image posted successfully.")
        return result.data.get("id")
    except Exception as e:
        logger.error("Failed to post tweet with image.", exc_info=True)
        return None


def get_meme_files(folder: str, formats: tuple) -> list:
    """Fetch valid meme files from a folder."""
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder {folder} does not exist.")
    return [f for f in os.listdir(folder) if f.lower().endswith(formats)]


class MemePoster:
    def __init__(self, client, api, meme_folder=MEMES_FOLDER_NAME, logger=None):
        self.client = client
        self.api = api
        self.meme_folder = os.path.abspath(meme_folder)
        self.logger = logger or logging.getLogger(__name__)

    def post_meme(self) -> Optional[str]:
        """Post a random meme with a caption."""
        try:
            meme_files = get_meme_files(self.meme_folder, SUPPORTED_MEME_FORMATS)
            if not meme_files:
                self.logger.warning("No memes available.")
                return None

            meme = random.choice(meme_files)
            caption = random.choice(MEME_CAPTIONS)
            meme_path = os.path.join(self.meme_folder, meme)

            return post_image_with_tweet(
                self.client, self.api, caption, meme_path, self.logger
            )
        except Exception as e:
            self.logger.error(f"Error posting meme: {e}", exc_info=True)
            return None

    def should_post_meme(self) -> bool:
        """Determine if the bot should post a meme."""
        return random.random() < MEME_POSTING_CHANCE
