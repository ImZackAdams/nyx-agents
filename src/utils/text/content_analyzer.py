"""
Handles content analysis including sentiment analysis and content categorization.
"""

from nltk.sentiment import SentimentIntensityAnalyzer
from typing import Dict

# CHANGED: replace the relative import with an absolute import to the top-level config module
from config.personality_config import Category


class ContentAnalyzer:
    """Analyzes content sentiment and categories."""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self._initialize_category_keywords()
        
    def _initialize_category_keywords(self):
        """Initialize category keywords mapping (aligned to current Category enum)."""
        self.category_keywords = {
            Category.EDUCATION: [
                "explain", "guide", "how to", "lesson", "learn", "why", "what is"
            ],
            Category.TECH_DISCUSSION: [
                "agent", "agents", "automation", "workflow", "tools", "protocol",
                "system", "infrastructure", "code", "technical"
            ],
            Category.PRODUCTIVITY: [
                "productivity", "habit", "workflow", "speed", "focus", "time", "tool"
            ],
            Category.CULTURE: [
                "culture", "community", "internet", "builders", "memes", "lore"
            ],
            Category.HUMOR: [
                "joke", "meme", "lol", "shitpost", "chaos", "sarcasm"
            ],
            Category.GENERAL: []
        }
        
    def analyze_sentiment(self, text: str) -> str:
        """
        Analyzes text sentiment and returns 'positive', 'negative', or 'neutral'.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            str: Sentiment label ('positive', 'negative', or 'neutral').
        """
        try:
            scores = self.get_sentiment_scores(text)
            return self._get_sentiment_label(scores)
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            return "neutral"
            
    def get_sentiment_scores(self, text: str) -> Dict[str, float]:
        """
        Get detailed sentiment scores for the text.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            Dict[str, float]: Dictionary containing sentiment scores.
        """
        return self.sentiment_analyzer.polarity_scores(text)
            
    def _get_sentiment_label(self, scores: Dict[str, float]) -> str:
        """
        Convert sentiment scores to a label.
        
        Args:
            scores (Dict[str, float]): Sentiment scores from the analyzer.
            
        Returns:
            str: Sentiment label ('positive', 'negative', or 'neutral').
        """
        if scores["compound"] > 0.05:
            return "positive"
        elif scores["compound"] < -0.05:
            return "negative"
        return "neutral"
            
    def categorize_prompt(self, prompt: str) -> Category:
        """
        Categorizes the input prompt based on keyword presence.
        
        Args:
            prompt (str): The prompt to categorize.
            
        Returns:
            Category: The determined category enum.
        """
        prompt_lower = prompt.lower()
        
        for category, keywords in self.category_keywords.items():
            if self._contains_keywords(prompt_lower, keywords):
                return category
                
        return Category.GENERAL
        
    def _contains_keywords(self, text: str, keywords: list) -> bool:
        """
        Check if text contains any of the keywords.
        
        Args:
            text (str): Text to check.
            keywords (list): List of keywords to look for.
            
        Returns:
            bool: True if any keyword is found, False otherwise.
        """
        return any(keyword in text for keyword in keywords)
