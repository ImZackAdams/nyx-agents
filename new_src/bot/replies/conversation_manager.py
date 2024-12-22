# bot/services/conversation_manager.py
import collections
from typing import List, Dict, Optional

class ConversationManager:
    """
    Manages conversation history for multi-turn conversations on Twitter.
    Stores the latest messages for each conversation (e.g., keyed by tweet ID).
    """

    def __init__(self, max_history_length: int = 5):
        # max_history_length: how many past messages to store
        self.max_history_length = max_history_length
        # Using a dict: {tweet_id: deque([message1, message2, ...])}
        self.histories: Dict[str, collections.deque] = {}

    def add_message(self, tweet_id: str, message: str) -> None:
        """
        Add a new message to the conversation history.
        If the history for this tweet_id doesn't exist, create it.
        """
        if tweet_id not in self.histories:
            self.histories[tweet_id] = collections.deque(maxlen=self.max_history_length)
        self.histories[tweet_id].append(message)

    def get_history(self, tweet_id: str) -> List[str]:
        """
        Return the current conversation history for a given tweet_id.
        Returns an empty list if no history exists.
        """
        if tweet_id in self.histories:
            return list(self.histories[tweet_id])
        return []
