import os
import random
import logging
from typing import Optional, Tuple
from bot.prompts import MEME_CAPTIONS
from bot.twitter_client import post_image_with_tweet
from bot.configs.posting_config import (
    MEME_POSTING_CHANCE,
    SUPPORTED_MEME_FORMATS,
    MEMES_FOLDER_NAME
)

class MemeHandler:
    """Handles the selection and posting of memes."""
    
    def __init__(self, client, api, logger: Optional[logging.Logger] = None):
        """Initialize MemeHandler.
        
        Args:
            client: Twitter client for API v2
            api: Twitter API v1.1 for media uploads
            logger: Optional logger instance
        """
        self.client = client
        self.api = api
        self.logger = logger or logging.getLogger(__name__)
        # Build memes folder path at initialization
        self.memes_folder = os.path.join(os.getcwd(), MEMES_FOLDER_NAME)
        
    def _validate_memes_folder(self) -> bool:
        """Check if memes folder exists and is accessible."""
        if not os.path.exists(self.memes_folder):
            self.logger.error(f"Memes folder not found at {self.memes_folder}")
            return False
        return True
        
    def _get_available_memes(self) -> list:
        """Get list of available meme files."""
        if not self._validate_memes_folder():
            return []
            
        return [
            f for f in os.listdir(self.memes_folder) 
            if f.lower().endswith(SUPPORTED_MEME_FORMATS)
        ]
        
    def _select_meme(self) -> Tuple[Optional[str], Optional[str]]:
        """Select a random meme and caption.
        
        Returns:
            Tuple of (meme_path, caption) or (None, None) if no memes available
        """
        available_memes = self._get_available_memes()
        
        if not available_memes:
            self.logger.warning("No memes available to post")
            return None, None
            
        selected_meme = random.choice(available_memes)
        caption = random.choice(MEME_CAPTIONS)
        meme_path = os.path.join(self.memes_folder, selected_meme)
        
        return meme_path, caption
        
    def post_meme(self) -> Optional[str]:
        """Post a meme with a caption.
        
        Returns:
            str: Tweet ID if successful, None otherwise
        """
        try:
            meme_path, caption = self._select_meme()
            if not meme_path:
                return None
                
            self.logger.info(f"Posting meme: {os.path.basename(meme_path)}")
            result = post_image_with_tweet(
                self.client,
                self.api,
                caption,
                meme_path,
                self.logger
            )
            
            if result:
                self.logger.info("Meme posted successfully")
                return result
                
            self.logger.error("Failed to post meme")
            return None
            
        except Exception as e:
            self.logger.error(f"Error posting meme: {str(e)}", exc_info=True)
            return None
            
    def should_post_meme(self) -> bool:
        """Determine if we should post a meme based on configuration."""
        return random.random() < MEME_POSTING_CHANCE